# -*- coding: utf-8 -*-

"""CLI commands offered by this package."""

from __future__ import absolute_import, division, print_function

import click

from .api import Client


@click.group()
@click.pass_context
def cli(ctx):
    ctx.obj = Client()


@cli.command()
@click.argument('id_list', nargs=-1, type=str)
@click.option('-t', '--timeout', nargs=1, type=int)
@click.pass_obj
def download(client, id_list, timeout):
    client.download(id_list, timeout=timeout)


@cli.command()
@click.argument('id_list', nargs=-1, type=str)
@click.option('-t', '--timeout', nargs=1, type=int)
@click.pass_obj
def fetch(client, id_list, timeout):
    click.echo(client.fetch(id_list, timeout=timeout))


@cli.command()
@click.argument('query', nargs=1, type=str)
@click.option('-i', '--ids', is_flag=True)
@click.option('-t', '--timeout', nargs=1, type=int)
@click.pass_obj
def find(client, query, ids, timeout):
    click.echo(client.find(query, ids=ids, timeout=timeout), nl=not ids)
