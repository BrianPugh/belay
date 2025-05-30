from belay._minify import minify

expected = """def foo():
 if True:
  0
"""


def test_minify_simple():
    res = minify(
        """def foo():
    if True:
        pass
"""
    )
    assert res == expected


def test_minify_leading_indent():
    res = minify(
        """    def foo():
        if True:
            pass
"""
    )
    assert res == expected


def test_minify_remove_inline_comments():
    res = minify(
        """def foo():
    if True:  # This is a comment
        pass
"""
    )
    assert res == expected


def test_minify_remove_whole_line_comments():
    res = minify(
        """def foo():
    # This is a comment
    if True:
        pass
"""
    )
    expected = """def foo():

 if True:
  0
"""

    assert res == expected


def test_minify_docstring():
    res = minify(
        """def foo():
    '''
    This is a multiline docstring
    '''
    if True:
        return "this is a literal"
"""
    )
    expected = """def foo():
 0


 if True:
  return "this is a literal"
"""

    assert res == expected


def test_minify_leading_indent_docstring():
    res = minify(
        """    def foo():
        '''
        This is a multiline docstring
        '''
        if True:
            return "this is a literal"
"""
    )
    expected = """def foo():
 0


 if True:
  return "this is a literal"
"""

    assert res == expected


def test_minify_ops():
    res = minify(
        """def foo():
    bar = 5 * 6 @ 1 - 2
    if bar <= 6:
        baz = True
    return "test test"
"""
    )
    expected = """def foo():
 bar=5*6@1-2
 if bar<=6:
  baz=True
 return "test test"
"""
    assert res == expected


def test_minify_newline_pass_0():
    """Replicated issue https://github.com/BrianPugh/belay/issues/167."""
    res = minify(
        """
print(src_code)
l1 =[
'foo','bar']
l2 =['foo','bar']
l3 =['foo',
'bar']
l4 =['foo',
'bar',
'baz']
l5 =[
'foo','foo',
'bar','bar',
'baz','baz']
print ('l1',l1 )
print ('l2',l2 )
print ('l3',l3 )
print ('l4',l4 )
print ('l5',l5 )
"""
    )
    expected = """
print(src_code)
l1=[
'foo','bar']
l2=['foo','bar']
l3=['foo',
'bar']
l4=['foo',
'bar',
'baz']
l5=[
'foo','foo',
'bar','bar',
'baz','baz']
print('l1',l1)
print('l2',l2)
print('l3',l3)
print('l4',l4)
print('l5',l5)
"""
    assert res == expected


def test_minify_leading_string_expression():
    res = minify("'b' in foo")
    assert res == "'b' in foo"
