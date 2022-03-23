"""
 Copyright (c) 2022 OctMedia

 Permission is hereby granted, free of charge, to any person obtaining a copy of
 this software and associated documentation files (the "Software"), to deal in
 the Software without restriction, including without limitation the rights to
 use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
 the Software, and to permit persons to whom the Software is furnished to do so,
 subject to the following conditions:

 The above copyright notice and this permission notice shall be included in all
 copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 """

import sys

import lrparsing
from lrparsing import Keyword, List, Prio, Ref, THIS, Token, Tokens, Repeat

from maya import cmds

G_EXPR_NAME = None


class ExprParser(lrparsing.Grammar):

    class T(lrparsing.TokenRegistry):
        variable = Token(re="[A-Za-z_0-9]*\.[A-Za-z_][A-Za-z_0-9\[\]\.]*")
        number = Token(re="[-+]?\d*\.\d+|\d+")
        func_name = Token(re="[A-Za-z_][A-Za-z_0-9]*")

    expr = Ref("expr")
    call = T.func_name + '(' + List(expr, ',') + ')'
    atom = T.variable | T.number
    brackets = '(' + expr + ')'
    expr = call | brackets | Prio(atom, Tokens("+ -") >> THIS, THIS << Tokens("* / %") << THIS, THIS << Tokens("+ -") << THIS, THIS << Tokens("== !=") << THIS)
    sentence = T.variable + Token('=') + expr
    block = '{' + List(sentence, ";", opt=True) + '}'
    condition = Keyword('if') + expr + block + Keyword('else') + block
    segment = condition | sentence + ";"
    START = Repeat(segment)
    COMMENTS = Token(re="//[^\n]*\n")


def plug_dimension(plug):
    type_t = cmds.getAttr(plug, t=True)
    assert type_t in {'doubleLinear', 'double'}, plug
    return 1


def process_segment(node):
    assert node[0].name == 'segment'
    if node[1][0].name == 'condition':
        process_condition(node[1])
    elif node[1][0].name == 'sentence':
        process_sentence(node[1])
    else:
        assert False, node


def process_condition(node):
    raise RuntimeError("[Nemo]expression IF is not supported")

    assert node[0].name == 'condition'
    condition = cmds.createNode('condition')
    expr = node[2][1][2]
    assert expr[1][0].name == 'expr'
    left = process_expr(expr[1])
    assert expr[3][0].name == 'expr'
    right = process_expr(expr[3])
    set_or_connect_plug(condition + '.firstTerm', left)
    set_or_connect_plug(condition + '.secondTerm', right)

    assert expr[2][1] == '=='


def process_sentence(node):
    assert node[0].name == 'sentence'
    assert node[1][0].name == 'T.variable'
    left = node[1][1]
    assert node[2][1] == '='
    assert node[3][0].name == 'expr'

    if left.startswith('.'):
        left = G_EXPR_NAME + left.replace('O[', 'output[')

    right = process_expr(node[3])
    if cmds.getAttr(left, lock=True):
        cmds.setAttr(left, lock=False)
    cmds.connectAttr(right, left, force=True)


def set_or_connect_plug(plug, source):
    if isinstance(source, basestring):
        cmds.connectAttr(source, plug)
    else:
        cmds.setAttr(plug, source)


def process_brackets(node):
    assert node[0].name == 'brackets'
    return process_expr(node[2])


def process_expr(node):
    assert node[0].name == 'expr'
    if len(node) - 1 == 3:
        assert node[1][0].name == 'expr'
        left = process_expr(node[1])
        assert node[3][0].name == 'expr'
        right = process_expr(node[3])

        if node[2][1] in {'*', '/'}:
            maya_node = cmds.createNode('multiplyDivide')
            if node[2][1] == '/':
                cmds.setAttr(maya_node + '.operation', 2)
            set_or_connect_plug(maya_node + '.input1X', left)
            set_or_connect_plug(maya_node + '.input2X', right)
            return maya_node + '.outputX'
        elif node[2][1] in {'+', '-'}:
            maya_node = cmds.createNode('plusMinusAverage')
            if node[2][1] == '-':
                cmds.setAttr(maya_node + '.operation', 2)
            set_or_connect_plug(maya_node + '.input1D[0]', left)
            set_or_connect_plug(maya_node + '.input1D[1]', right)
            return maya_node + '.output1D'
        elif node[2][1] == '%':
            animCurve = cmds.createNode('animCurveUU')
            cmds.setKeyframe(animCurve, float=0, v=0, itt='linear', ott='linear')
            cmds.setKeyframe(animCurve, float=right - 1E-10, v=1, itt='linear', ott='linear')
            cmds.setAttr('{}.preInfinity'.format(animCurve), 3)
            cmds.setAttr('{}.postInfinity'.format(animCurve), 3)
            set_or_connect_plug('{}.input'.format(animCurve), left)
            return '{}.output'.format(animCurve)
        else:
            assert False
    elif len(node) - 1 == 1:
        if node[1][0].name == 'atom':
            return process_atom(node[1])
        elif node[1][0].name == 'call':
            return process_call(node[1])
        elif node[1][0].name == 'brackets':
            return process_brackets(node[1])
        else:
            assert False
    elif len(node) - 1 == 2:
        assert node[1][1] == '-'
        return process_negative(node[2])
    else:
        assert False


def process_negative(node):
    maya_node = cmds.createNode('multiplyDivide')
    set_or_connect_plug(maya_node + '.input1X', process_expr(node))
    cmds.setAttr(maya_node + '.input2X', -1)
    return maya_node + '.outputX'


def process_atom(node):
    assert node[0].name == 'atom'
    if node[1][0].name == 'T.variable':
        if node[1][1].startswith('.'):
            return G_EXPR_NAME + node[1][1].replace('I[', 'input[').replace('O[', 'output[')
        return node[1][1]
    elif node[1][0].name == 'T.number':
        return float(node[1][1])
    else:
        assert False


def process_call(node):
    assert node[0].name == 'call'
    if node[1][1] in {'min', 'max'}:
        left = process_expr(node[3])
        right = process_expr(node[5])
        maya_node = cmds.createNode('clamp')
        set_or_connect_plug(maya_node + '.inputR', left)
        if node[1][1] == 'min':
            set_or_connect_plug(maya_node + '.maxR', right)
            cmds.setAttr(maya_node + '.minR', sys.float_info.min)
        else:
            assert node[1][1] == 'max'
            set_or_connect_plug(maya_node + '.minR', right)
            cmds.setAttr(maya_node + '.maxR', sys.float_info.max)
        return maya_node + '.outputR'
    elif node[1][1] == 'sin':
        multBy2 = cmds.createNode("multDoubleLinear")
        cmds.setAttr("{}.input2".format(multBy2), 2)  # To degrees
        cmds.connectAttr(process_expr(node[3]), "{}.input1".format(multBy2))
        quat = cmds.createNode("eulerToQuat")
        cmds.connectAttr("{}.output".format(multBy2), "{}.inputRotateX".format(quat))
        return "{}.outputQuat.outputQuatX".format(quat)
    else:
        assert False, node[1][1]


def convert_all_expressions():
    global G_EXPR_NAME
    G_EXPR_NAME = None
    for expression_node in cmds.ls(type='expression'):
        try:
            G_EXPR_NAME = expression_node
            is_expression_valid = True
            if not cmds.listConnections('{}.input'.format(expression_node)):
                is_expression_valid = False
            if is_expression_valid:
                text = cmds.expression(expression_node, q=True, s=True) + '\n'
                parse_tree = ExprParser.parse(text)
                assert parse_tree[0].name == 'START'
                for segment in parse_tree[1:]:
                    assert segment[0].name == 'segment'
                    process_segment(segment)
            cmds.delete(expression_node)
        except Exception:
            raise RuntimeError('[Nemo]failed converting expression "{}"'.format(expression_node))
    cmds.select(cl=True)


# ast = ExprParser.parse(text)
# print(ExprParser.repr_parse_tree(ast))