import pytest
from load_scores import load_scores


@pytest.fixture
def make_csv(tmp_path):
    """테스트용 임시 CSV 파일을 생성하는 헬퍼 픽스처"""
    def _make_csv(content: str, encoding: str = "utf-8", filename: str = "scores.csv"):
        file_path = tmp_path / filename
        file_path.write_text(content, encoding=encoding)
        return file_path
    return _make_csv


# ==========================================
# 1. 정상 동작 및 조건·제약 테스트
# ==========================================

def test_valid_basic_and_order_preservation(make_csv):
    """기본 정상 입력, 입력 순서 유지, 동명이인 보존 검증"""
    content = (
        "name,score\n"
        "김철수,85\n"
        "이영희,92\n"
        "김철수,70\n"  # 동명이인
    )
    path = make_csv(content)
    kept, skipped = load_scores(path)

    assert kept == [
        ("김철수", 85),
        ("이영희", 92),
        ("김철수", 70),
    ]
    assert skipped == []


def test_quoted_comma_whitespace_trim_and_utf8_bom(make_csv):
    """CSV 따옴표 안 쉼표 처리, 이름·점수 앞뒤 공백 제거, UTF-8 BOM 허용 검증"""
    content = (
        "name,score\n"
        '"Kim, Minji", 95 \n'
        '  "  Lee, Junho  "  ,  88  \n'
    )
    # utf-8-sig 인코딩으로 저장하여 파일 맨 앞에 UTF-8 BOM(\ufeff) 삽입
    path = make_csv(content, encoding="utf-8-sig")
    kept, skipped = load_scores(path)

    assert kept == [
        ("Kim, Minji", 95),
        ("Lee, Junho", 88),
    ]
    assert skipped == []


def test_blank_lines_ignored_without_skip_record(make_csv):
    """빈 행은 skipped에 기록하지 않고 건너뛰며, 이후 행 번호를 정확히 유지하는지 검증"""
    content = (
        "name,score\n"
        "\n"
        "   \n"
        "박지성,80\n"
        "\n"
        "손흥민,abc\n"  # 헤더(1), 빈줄(2), 공백줄(3), 박지성(4), 빈줄(5), 손흥민(6)
    )
    path = make_csv(content)
    kept, skipped = load_scores(path)

    assert kept == [("박지성", 80)]
    assert skipped == [
        (6, "손흥민,abc", "점수가 정수가 아님"),
    ]


# ==========================================
# 2. 경계값 테스트
# ==========================================

def test_header_only_file(make_csv):
    """헤더만 있는 파일은 ([], []) 반환"""
    path = make_csv("name,score\n")
    kept, skipped = load_scores(path)

    assert kept == []
    assert skipped == []


@pytest.mark.parametrize(
    "score_str, expected_kept, expected_reason",
    [
        ("0", True, None),          # 하한 경계값 (허용)
        ("100", True, None),        # 상한 경계값 (허용)
        ("101", False, "점수가 0~100 밖"),  # 상한 초과 경계값 (제외)
        ("-1", False, "점수가 0~100 밖"),   # 하한 미만 경계값 (제외)
    ],
)
def test_score_boundary_values(make_csv, score_str, expected_kept, expected_reason):
    """점수 경계값(0, 100, 101, -1) 검증"""
    line = f"홍길동,{score_str}"
    path = make_csv(f"name,score\n{line}\n")
    kept, skipped = load_scores(path)

    if expected_kept:
        assert kept == [("홍길동", int(score_str))]
        assert skipped == []
    else:
        assert kept == []
        assert skipped == [(2, line, expected_reason)]


# ==========================================
# 3. 예외 상황 및 오류 처리 테스트
# ==========================================

def test_file_not_found_raises_error(tmp_path):
    """존재하지 않는 경로 전달 시 FileNotFoundError 발생"""
    non_existent_path = tmp_path / "does_not_exist.csv"
    with pytest.raises(FileNotFoundError):
        load_scores(non_existent_path)


@pytest.mark.parametrize(
    "raw_line, expected_reason",
    [
        # 1) 열 개수가 2가 아님
        ("김철수", "열 개수가 2가 아님"),
        ("김철수,80,추가열", "열 개수가 2가 아님"),
        (",", "이름이 비어 있음"),  # 열은 2개이므로 이름 공백 검사로 진입하는지 확인
        # 2) 이름이 비어 있음
        (",85", "이름이 비어 있음"),
        ("   ,85", "이름이 비어 있음"),
        ('"",85', "이름이 비어 있음"),
        ('"   ",85', "이름이 비어 있음"),
        # 3) 점수가 비어 있음 (0점으로 대체하지 않고 제외)
        ("이영희,", "점수가 비어 있음"),
        ("이영희,   ", "점수가 비어 있음"),
        ('이영희,""', "점수가 비어 있음"),
        # 4) 점수가 정수가 아님
        ("박민수,85.5", "점수가 정수가 아님"),
        ("박민수,90.0", "점수가 정수가 아님"),
        ("박민수,만점", "점수가 정수가 아님"),
        ("박민수,NaN", "점수가 정수가 아님"),
        # 5) 점수가 0~100 밖
        ("최수진,-5", "점수가 0~100 밖"),
        ("최수진,105", "점수가 0~100 밖"),
    ],
)
def test_invalid_rows_skipped_with_exact_reasons(make_csv, raw_line, expected_reason):
    """각종 잘못된 데이터 행의 제외 사유 문구 및 행 번호 기록 검증"""
    content = (
        "name,score\n"
        "정상학생1,75\n"
        f"{raw_line}\n"
        "정상학생2,90\n"
    )
    path = make_csv(content)
    kept, skipped = load_scores(path)

    # 잘못된 행이 있어도 중단하지 않고 앞뒤 정상 행을 모두 처리해야 함
    assert kept == [
        ("정상학생1", 75),
        ("정상학생2", 90),
    ]
    assert skipped == [
        (3, raw_line, expected_reason),
    ]


# ==========================================
# 4. 부수 효과(원본 파일 수정 금지) 테스트
# ==========================================

def test_original_file_is_not_modified(make_csv):
    """함수 실행 후 원본 CSV 파일의 내용과 바이트가 전혀 변경되지 않았는지 검증"""
    original_content = (
        "name,score\n"
        "강다니엘,\n"
        "유재석,100\n"
        "잘못된행\n"
    )
    path = make_csv(original_content, encoding="utf-8-sig")
    before_bytes = path.read_bytes()

    load_scores(path)

    after_bytes = path.read_bytes()
    assert before_bytes == after_bytes
