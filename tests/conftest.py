# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

from click.testing import CliRunner
from pytest import fixture


@fixture(scope='function')
def runner():
    return CliRunner()
