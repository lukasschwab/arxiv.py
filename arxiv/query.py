from enum import Enum

class Query(object):
  _query_string: str

  # TODO: need helper to build query_string with a key/val pair, e.g. cat:ABC
  def __init__(self, query_string: str = ""):
    self._query_string = query_string
  
  # FIXME: check if value is a Category?
  def attribute(attribute: "Query.Attribute", value: str) -> "Query":
    return Query('{}:"{}"'.format(attribute.value, value))
  
  def __compose(self, other: "Query", operator: "Query.Operator"):
    return Query("({}) {} ({})".format(
      self._query_string,
      operator.value,
      other._query_string,
    ))

  def AND(self, other: "Query"):
    return self.__compose(other, Query.Operator.And)
  
  def OR(self, other: "Query"):
    return self.__compose(other, Query.Operator.Or)
  
  def ANDNOT(self, other: "Query"):
    return self.__compose(other, Query.Operator.AndNot)

  class Operator(Enum):
    And = "AND"
    Or = "OR"
    AndNot = "ANDNOT"

  def to_string(self):
    return self._query_string

class Attribute(Enum):
  """
  See https://arxiv.org/help/api/user-manual#query_details.
  """
  Title = "ti"
  Author = "au"
  Abstract = "abs"
  Comment = "co"
  JournalReference = "jr"
  Category = "cat"
  ReportNumber = "rn"
  ID = "id" # NOTE: prefer id_list when possible.
  All = "all"
