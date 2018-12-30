from __future__ import print_function
import arxiv

# Returns the object id.
def custom_slugify(obj):
    return obj.get('pdf_url').split('/')[-1]

paper1 = arxiv.query(id_list=["1707.08567"])[0]
paper2 = {"pdf_url": "http://arxiv.org/pdf/1707.08567v1",
          "title": "The Paper Title"}

for paper in [paper1, paper2]:
    # Default behavior
    print(arxiv.download(paper))
    # Specify subdirectory
    print(arxiv.download(paper, dirpath="downloads"))
    print(arxiv.download(paper, dirpath="downloads/"))
    # Specify slugify without subdir
    print(arxiv.download(paper, slugify=custom_slugify))
    # Specify slugify with subdir
    print(arxiv.download(paper, slugify=custom_slugify, dirpath="downloads"))
    print(arxiv.download(paper, slugify=custom_slugify, dirpath="downloads/"))
