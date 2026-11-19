import pytest


def find_max(scores):
    biggest = scores[0]
    for i in range(1, len(scores) - 1):
        if scores[i] > biggest:
            biggest = scores[i]
    return biggest


# 1. 정상 케이스 (Normal)
@pytest.mark.parametrize(
    "scores, expected",
    [
        ([10, 50, 30, 20], 50),          # 일반적인 양수 리스트
        ([-50, -10, -30, -20], -10),     # 음수로만 이루어진 리스트
        ([-10, 0, 5, -3], 5),            # 음수, 0, 양수 혼합
        ([3.14, 9.81, 2.71, 1.41], 9.81), # 실수(float) 포함
        ([7, 7, 7, 7], 7),               # 모든 요소가 동일한 경우
    ],
)
def test_find_max_normal(scores, expected):
    assert find_max(scores) == expected


# 2. 경계값 케이스 (Boundary)
def test_find_max_single_element():
    """요소가 1개뿐인 경우"""
    assert find_max([42]) == 42


def test_find_max_at_first_index():
    """최댓값이 첫 번째 인덱스에 위치한 경우"""
    assert find_max([100, 20, 30, 40]) == 100


def test_find_max_at_last_index():
    """최댓값이 마지막 인덱스에 위치한 경우 (현재 구현의 버그 검출용)"""
    assert find_max([10, 20, 30, 99]) == 99


# 3. 예외 케이스 (Exception)
def test_find_max_empty_list():
    """빈 리스트 입력 시 IndexError 발생 확인"""
    with pytest.raises(IndexError):
        find_max([])


def test_find_max_none_input():
    """None 입력 시 TypeError 발생 확인"""
    with pytest.raises(TypeError):
        find_max(None)


def test_find_max_uncomparable_types():
    """서로 비교할 수 없는 타입(문자열과 숫자)이 섞여 있을 때 TypeError 발생 확인"""
    with pytest.raises(TypeError):
        find_max([10, "20", 30])
