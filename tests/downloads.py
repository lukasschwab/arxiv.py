import arxiv

paper = arxiv.query(id_list=["1707.08567"])[0]

# Default behavior
print arxiv.download(paper)

# Specify subdirectory
print arxiv.download(paper, dirpath="downloads")
print arxiv.download(paper, dirpath="downloads/")

# Returns the object id.
def custom_slugify(obj):
    return obj.get('id').split('/')[-1]

# Specify slugify without subdir
print arxiv.download(paper, slugify=custom_slugify)

# Specify slugify with subdir
print arxiv.download(paper, slugify=custom_slugify, dirpath="downloads")
print arxiv.download(paper, slugify=custom_slugify, dirpath="downloads/")
