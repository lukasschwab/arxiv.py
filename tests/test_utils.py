# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

from mock import call, patch

from arxiv.utils import drip, has


def _square(n):
    return n**2


def test_drip_generalizes_map_when_t_equals_zero():
    assert drip(_square, [1, 2, 3]) == [1, 4, 9]


@patch('arxiv.utils.sleep')
def test_drip_sleeps_zero_times_on_a_list_of_zero_elements(sleep):
    assert drip(_square, [], t=1) == []

    sleep.assert_not_called()


@patch('arxiv.utils.sleep')
def test_drip_sleeps_zero_times_on_a_list_of_one_element(sleep):
    assert drip(_square, [1], t=1) == [1]

    sleep.assert_not_called()


@patch('arxiv.utils.sleep')
def test_drip_sleeps_n_minus_one_times_on_a_list_of_n_elements(sleep):
    assert drip(_square, [1, 2, 3], t=1) == [1, 4, 9]

    sleep.assert_has_calls([call(1), call(1)])


def test_has_returns_true_when_d_has_key_k():
    assert has({'foo': 'bar'}, 'foo')


def test_has_returns_false__when_d_has_key_k_with_value_None():
    assert not has({'foo': None}, 'foo')
