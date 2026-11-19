"""배포 명세로 설계한 정상·예외·경계값 검사."""
from pathlib import Path
import runpy
import sys

import pytest

from load_scores import load_scores

BASE = Path(__file__).resolve().parent


def write_csv(tmp_path, content):
    path = tmp_path / "input.csv"
    path.write_text(content, encoding="utf-8")
    return path


def test_정상_파일을_읽는다(tmp_path):
    path = write_csv(tmp_path, "name,score\n가람,88\n나래,75\n")
    assert load_scores(path) == ([("가람", 88), ("나래", 75)], [])


def test_빈_줄은_건너뛴다(tmp_path):
    path = write_csv(tmp_path, "name,score\n가람,88\n\n나래,75\n")
    assert load_scores(path) == ([("가람", 88), ("나래", 75)], [])


def test_이름에_쉼표가_있어도_읽는다(tmp_path):
    path = write_csv(tmp_path, 'name,score\n"김,쉼표",77\n')
    assert load_scores(path) == ([("김,쉼표", 77)], [])


def test_없는_파일이면_오류가_난다(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_scores(tmp_path / "missing.csv")


def test_헤더만_있으면_빈_결과(tmp_path):
    assert load_scores(write_csv(tmp_path, "name,score\n")) == ([], [])


@pytest.mark.parametrize(
    "점수,유효한가", [(-1, False), (0, True), (1, True), (99, True), (100, True), (101, False)]
)
def test_점수_경계값(tmp_path, 점수, 유효한가):
    path = write_csv(tmp_path, f"name,score\n가람,{점수}\n")
    if 유효한가:
        assert load_scores(path) == ([("가람", 점수)], [])
    else:
        assert load_scores(path) == ([], [(2, f"가람,{점수}", "점수가 0~100 밖")])


@pytest.mark.parametrize("row", ["가람", "가람,88,비고"])
def test_열_개수가_틀리면_원본과_이유를_기록한다(tmp_path, row):
    path = write_csv(tmp_path, f"name,score\n{row}\n")
    assert load_scores(path) == ([], [(2, row, "열 개수가 2가 아님")])


def test_이름이_비어_있으면_기록한다(tmp_path):
    path = write_csv(tmp_path, "name,score\n   ,90\n")
    assert load_scores(path) == ([], [(2, "   ,90", "이름이 비어 있음")])


def test_빈_점수를_0점으로_바꾸지_않는다(tmp_path):
    path = write_csv(tmp_path, "name,score\n가람,\n")
    assert load_scores(path) == ([], [(2, "가람,", "점수가 비어 있음")])


@pytest.mark.parametrize("raw", ["결석", "88.5", "NaN"])
def test_정수가_아닌_점수를_기록한다(tmp_path, raw):
    path = write_csv(tmp_path, f"name,score\n가람,{raw}\n")
    assert load_scores(path) == ([], [(2, f"가람,{raw}", "점수가 정수가 아님")])


def test_동명이인을_모두_보존한다(tmp_path):
    path = write_csv(tmp_path, "name,score\n김하나,88\n김하나,91\n")
    assert load_scores(path) == ([("김하나", 88), ("김하나", 91)], [])


def test_BOM과_앞뒤_공백을_처리한다(tmp_path):
    path = write_csv(tmp_path, "\ufeffname,score\n 가람 , 77 \n")
    assert load_scores(path) == ([("가람", 77)], [])


def test_배포_scores의_전체_기록을_검증한다():
    assert load_scores(BASE / "scores.csv") == (
        [("김하나", 88), ("최,네번", 77), ("김하나", 91), ("윤보람", 64), ("서한별", 95)],
        [
            (3, "이두리,105", "점수가 0~100 밖"),
            (4, "박세찬,", "점수가 비어 있음"),
            (7, "정오름,-5", "점수가 0~100 밖"),
            (8, "한겨울,결석", "점수가 정수가 아님"),
            (9, "장미르,72,비고없음", "열 개수가 2가 아님"),
        ],
    )


def test_배포_weird의_전체_기록을_검증한다():
    assert load_scores(BASE / "weird.csv") == (
        [("한겨울", 77), ("윤보람", 88)],
        [
            (2, ",90", "이름이 비어 있음"),
            (3, "서한별,", "점수가 비어 있음"),
            (4, "서한별,", "점수가 비어 있음"),
            (5, "김,쉼표,1000", "점수가 0~100 밖"),
            (6, "이두리,-100", "점수가 0~100 밖"),
            (7, "박세찬,88.5", "점수가 정수가 아님"),
            (9, "장미르,7 2", "점수가 정수가 아님"),
        ],
    )


@pytest.mark.parametrize("explicit_path", [False, True])
def test_명령줄_실행의_출력을_검증한다(monkeypatch, capsys, explicit_path):
    monkeypatch.chdir(BASE)
    monkeypatch.setattr(sys, "argv", ["load_scores.py"] + (["scores.csv"] if explicit_path else []))
    runpy.run_path(str(BASE / "load_scores.py"), run_name="__main__")
    output = capsys.readouterr().out
    assert "읽은 줄 : 5개" in output
    assert "건너뛴 줄 : 5개" in output
    assert "김하나 88" in output and "김하나 91" in output
    assert "9행  장미르,72,비고없음" in output
