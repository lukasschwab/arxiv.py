import unittest
import arxiv
from arxiv import category

from typing import List

class TestQuery(unittest.TestCase):
  def test_simple_queries(self):
    q_empty = arxiv.Query()
    self.assertEqual(q_empty.to_string(), '')
    keywords = 'some keywords'
    q_keywords = arxiv.Query(keywords)
    self.assertEqual(q_keywords.to_string(), keywords)

  def test_attribute_queries(self):
    # Without and without spaces.
    for value in ['value', 'space value']:
      for attr in arxiv.Attribute:
        q = arxiv.Query.attribute(attr, value)
        self.assertEqual(q.to_string(), '{}:"{}"'.format(attr.value, value))

  def test_and(self):
    q1, q1_expected = arxiv.Query("a").AND(arxiv.Query("b")), '(a) AND (b)'
    self.assertEqual(q1.to_string(), '(a) AND (b)')
    q2 = arxiv.Query.attribute(arxiv.Attribute.Title, "title").AND(q1)
    self.assertEqual(q2.to_string(), '(ti:"title") AND ({})'.format(q1_expected))

  def test_or(self):
    q1, q1_expected = arxiv.Query("a").OR(arxiv.Query("b")), '(a) OR (b)'
    self.assertEqual(q1.to_string(), '(a) OR (b)')
    q2 = arxiv.Query.attribute(arxiv.Attribute.Title, "title").OR(q1)
    self.assertEqual(q2.to_string(), '(ti:"title") OR ({})'.format(q1_expected))

  def test_andnot(self):
    q_a, q_b = arxiv.Query('a'), arxiv.Query('b')
    q1, q1_expected = q_a.ANDNOT(q_b), '(a) ANDNOT (b)'
    self.assertEqual(q1.to_string(), q1_expected)
    q2 = arxiv.Query.attribute(arxiv.Attribute.Title, "title").ANDNOT(q1)
    self.assertEqual(q2.to_string(), '(ti:"title") ANDNOT ({})'.format(q1_expected))
    # Reverse order must yield a different condition.
    q_reverse = q_b.ANDNOT(q_a)
    self.assertEqual(q_reverse.to_string(), '(b) ANDNOT (a)')

  def test_composition(self):
    """Grab-bag for complex cases."""
    q_a, q_b = arxiv.Query('a'), arxiv.Query('b')
    self.assertEqual(
      q_a.AND(q_b).OR(q_a).ANDNOT(q_b).to_string(),
      '(((a) AND (b)) OR (a)) ANDNOT (b)'
    )
    q_title = arxiv.Query.attribute(arxiv.Attribute.Title, 'some title')
    self.assertEqual(
      q_title.ANDNOT(q_a).AND(q_b).OR(q_title).to_string(),
      '(((ti:"some title") ANDNOT (a)) AND (b)) OR (ti:"some title")'
    )
    self.assertEqual(
      q_title.ANDNOT(q_a.OR(q_b)).to_string(),
      '(ti:"some title") ANDNOT ((a) OR (b))'
    )
    self.assertEqual(
      (q_a.OR(q_b)).ANDNOT(q_title).to_string(),
      '((a) OR (b)) ANDNOT (ti:"some title")'
    )

class TestQuery_Integration(unittest.TestCase):
  def abbr_results(self, query: arxiv.Query) -> List[arxiv.Result.Author]:
      results = list(arxiv.Search(query.to_string(), max_results=10).results())
      self.assertTrue(len(results) > 0, '0 results for {}'.format(query.to_string()))
      return results

  def test_attributes(self):
    q_title = arxiv.Query.attribute(arxiv.Attribute.Title, "quantum")
    for result in self.abbr_results(q_title):
      self.assertIn("quantum", result.title.lower())
    q_author = arxiv.Query.attribute(arxiv.Attribute.Author, "karpathy")
    for result in self.abbr_results(q_author):
      self.assertTrue(any(["karpathy" in a.name.lower() for a in result.authors]))
    
  def test_operators(self):
    q_econ = arxiv.Query.attribute(
      arxiv.Attribute.Category,
      category.Economics.GeneralEconomics.value
    )
    q_qf = arxiv.Query.attribute(
      arxiv.Attribute.Category,
      category.QuantitativeFinance.Economics.value
    )
    q_cats_and = q_econ.AND(q_qf)
    for result in self.abbr_results(q_cats_and):
      self.assertIn(category.Economics.GeneralEconomics.value, result.categories)
      self.assertIn(category.QuantitativeFinance.Economics.value, result.categories)
    q_cats_xor = q_econ.OR(q_qf).ANDNOT(q_cats_and)
    for result in self.abbr_results(q_cats_xor):
      has_econ = category.Economics.GeneralEconomics.value in result.categories
      has_qf = category.QuantitativeFinance.Economics.value in result.categories
      self.assertTrue(has_econ or has_qf and not (has_econ and has_qf))
    q_karpathy = arxiv.Query.attribute(
      arxiv.Attribute.Author,
      "karpathy"
    ).AND(arxiv.Query.attribute(
      arxiv.Attribute.Title,
      "PixelCNN"
    ))
    results_karpathy = self.abbr_results(q_karpathy)
    for result in results_karpathy:
      self.assertTrue(any(["karpathy" in a.name.lower() for a in result.authors]))
      self.assertIn("pixelcnn", result.title.lower())
    # Aug. 30, 2021: only one article matches.
    self.assertEqual(len(results_karpathy), 1)
    self.assertEqual(results_karpathy[0].get_short_id(), "1701.05517v1")





    


# TODO: write integration tests using the live API.