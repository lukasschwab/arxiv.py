import click
import arxiv


@click.command()
@click.argument("arxiv-id", type=click.STRING)
def main(arxiv_id: str):
    paper = arxiv.query(id_list=[arxiv_id])[0]
    arxiv.download(paper)


if __name__ == "__main__":
    main()
