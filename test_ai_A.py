import pytest
from load_scores import load_scores


@pytest.fixture
def make_csv(tmp_path):
    """테스트용 임시 CSV 파일을 생성하는 헬퍼 픽스처"""
    def _make_csv(content: str, encoding: str = "utf-8") -> str:
        file_path = tmp_path / "test_scores.csv"
        file_path.write_text(content, encoding=encoding)
        return str(file_path)
    return _make_csv


# =====================================================================
# 1. 정상 동작 (Normal Cases)
# =====================================================================

def test_valid_rows_and_whitespace_stripping(make_csv):
    """정상 데이터 읽기 및 이름/점수 앞뒤 공백 제거 검증"""
    csv_data = (
        "이름,점수\n"
        "홍길동,85\n"
        "  김철수  ,  92  \n"
        "이영희,70\n"
    )
    path = make_csv(csv_data)
    kept, skipped = load_scores(path)

    assert kept == [("홍길동", 85), ("김철수", 92), ("이영희", 70)]
    assert skipped == []


def test_duplicate_names_are_kept(make_csv):
    """v5 명세: 동명이인이 있을 경우 덮어쓰지 않고 모두 유지하는지 검증"""
    csv_data = (
        "이름,점수\n"
        "김민수,80\n"
        "박지훈,95\n"
        "김민수,65\n"
    )
    path = make_csv(csv_data)
    kept, skipped = load_scores(path)

    assert kept == [("김민수", 80), ("박지훈", 95), ("김민수", 65)]
    assert skipped == []


def test_utf8_bom_encoding(make_csv):
    """엑셀 등에서 저장된 UTF-8 BOM(utf-8-sig) 파일 정상 처리 검증"""
    csv_data = (
        "이름,점수\n"
        "최유리,88\n"
    )
    path = make_csv(csv_data, encoding="utf-8-sig")
    kept, skipped = load_scores(path)

    assert kept == [("최유리", 88)]
    assert skipped == []


def test_blank_lines_ignored_without_skipping_record(make_csv):
    """빈 줄은 skipped에 기록되지 않고 조용히 건너뛰며, 줄 번호(line_no)는 유지되는지 검증"""
    csv_data = (
        "이름,점수\n"
        "\n"
        "강하늘,90\n"
        "\n"
        "오류데이터\n"
    )
    path = make_csv(csv_data)
    kept, skipped = load_scores(path)

    assert kept == [("강하늘", 90)]
    # 1:헤더, 2:빈줄, 3:강하늘, 4:빈줄, 5:오류데이터
    assert skipped == [(5, "오류데이터", "열 개수가 2가 아님")]


# =====================================================================
# 2. 경계값 테스트 (Boundary Cases)
# =====================================================================

@pytest.mark.parametrize(
    "score_str, expected_valid, expected_reason",
    [
        ("-1", False, "점수가 0~100 밖"),  # 하한선 바로 아래 (불합격)
        ("0", True, None),                # 하한선 경계 (합격)
        ("1", True, None),                # 하한선 바로 위 (합격)
        ("99", True, None),               # 상한선 바로 아래 (합격)
        ("100", True, None),              # 상한선 경계 (합격)
        ("101", False, "점수가 0~100 밖"), # 상한선 바로 위 (불합격)
    ],
)
def test_score_boundaries(make_csv, score_str, expected_valid, expected_reason):
    """점수 허용 범위(0~100)의 경계값(-1, 0, 1, 99, 100, 101) 집중 검증"""
    csv_data = f"이름,점수\n테스터,{score_str}\n"
    path = make_csv(csv_data)
    kept, skipped = load_scores(path)

    if expected_valid:
        assert kept == [("테스터", int(score_str))]
        assert skipped == []
    else:
        assert kept == []
        assert skipped == [(2, f"테스터,{score_str}", expected_reason)]


def test_header_only_and_empty_file(make_csv):
    """명세 ②: 헤더만 있는 경우 및 완전히 빈 파일일 때 ([], []) 반환 검증"""
    # 헤더만 있는 경우
    path_header = make_csv("이름,점수\n")
    assert load_scores(path_header) == ([], [])

    # 완전히 빈 파일인 경우
    path_empty = make_csv("")
    assert load_scores(path_empty) == ([], [])


# =====================================================================
# 3. 예외 및 오류 행 처리 (Exception & Invalid Row Cases)
# =====================================================================

def test_file_not_found_raises_error(tmp_path):
    """명세 ①: 존재하지 않는 파일 경로 전달 시 FileNotFoundError가 그대로 발생하는지 검증"""
    non_existent_path = str(tmp_path / "does_not_exist.csv")
    with pytest.raises(FileNotFoundError):
        load_scores(non_existent_path)


@pytest.mark.parametrize(
    "row_str, expected_reason",
    [
        # 명세 ③: 열 개수가 2가 아님
        ("홍길동", "열 개수가 2가 아님"),
        ("홍길동,90,추가열", "열 개수가 2가 아님"),
        # 명세 ⑥: 이름이 비어 있음 (공백만 있는 경우 포함)
        (",85", "이름이 비어 있음"),
        ("   ,85", "이름이 비어 있음"),
        # 명세 ④: 점수가 비었거나 정수가 아님
        ("홍길동,", "점수가 비어 있음"),
        ("홍길동,   ", "점수가 비어 있음"),
        ("홍길동,85.5", "점수가 정수가 아님"),
        ("홍길동,백점", "점수가 정수가 아님"),
        ("홍길동,NaN", "점수가 정수가 아님"),
        # 명세 ⑤: 점수가 0~100 밖
        ("홍길동,-50", "점수가 0~100 밖"),
        ("홍길동,150", "점수가 0~100 밖"),
    ],
)
def test_invalid_rows_recorded_in_skipped(make_csv, row_str, expected_reason):
    """명세 ③~⑥: 각종 잘못된 형식의 행이 정확한 이유와 함께 skipped에 기록되는지 검증"""
    csv_data = f"이름,점수\n{row_str}\n"
    path = make_csv(csv_data)
    kept, skipped = load_scores(path)

    assert kept == []
    assert skipped == [(2, row_str, expected_reason)]


def test_mixed_valid_and_invalid_rows(make_csv):
    """정상 행, 빈 줄, 다양한 오류 행이 섞여 있을 때 통합 동작 및 줄 번호 정확도 검증"""
    csv_data = (
        "이름,점수\n"          # 1행 (헤더)
        "김영수,100\n"         # 2행 (정상)
        "열부족\n"             # 3행 (오류: 열 개수)
        "\n"                  # 4행 (빈 줄 - 무시)
        " ,50\n"              # 5행 (오류: 이름 비어 있음)
        "박소연,abc\n"         # 6행 (오류: 정수 아님)
        "정우성,105\n"         # 7행 (오류: 범위 밖)
        "김영수,0\n"           # 8행 (정상 - 동명이인 + 경계값 0)
    )
    path = make_csv(csv_data)
    kept, skipped = load_scores(path)

    assert kept == [
        ("김영수", 100),
        ("김영수", 0),
    ]
    assert skipped == [
        (3, "열부족", "열 개수가 2가 아님"),
        (5, " ,50", "이름이 비어 있음"),
        (6, "박소연,abc", "점수가 정수가 아님"),
        (7, "정우성,105", "점수가 0~100 밖"),
    ]
