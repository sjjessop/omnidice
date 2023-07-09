
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

# We only have to handle the operators which DRVs support, which simplifies
# things considerably.
binary_precedence = {
    **{op: 3 for op in ('@', '*', '/', '//')},
    **{op: 2 for op in ('+', '-')},
    **{op: 1 for op in ('<', '<=', '>', '>=', '==', '!=')},
}

class ExpressionTree(ABC):
    @abstractmethod
    def source(self) -> str:
        raise NotImplementedError
    def bracketed(self) -> str:
        return f'({self.source()})'

@dataclass(frozen=True)
class BinaryExpression(ExpressionTree):
    left: ExpressionTree
    right: ExpressionTree
    connective: str
    def source(self) -> str:
        # Our sub-expressions may or may not need brackets, depending on
        # operator precedence and associativity. We leave out some unnecessary
        # brackets, but keep a few for readability.
        precedence = binary_precedence[self.connective]
        def omit_left(left: BinaryExpression) -> bool:
            left_precedence = binary_precedence[left.connective]
            return (
                left_precedence > precedence
                # Chains of the same operator are easily read left-to-right,
                # except that comparisons are not (exactly) left-associative
                # because of Python's comparison-chaining rules.
                or (self.connective == left.connective and precedence > 1)
                # Mixed chains of + and - are easily read left-to-right. I'm
                # not convinced the same is true for the multiplicative
                # operators, for example a * b @ c * d could use brackets.
                or (precedence == left_precedence == 2)
            )
        def omit_right(right: BinaryExpression) -> bool:
            # Stuff on the right is more likely to need bracketing, because
            # everything associates left.
            return binary_precedence[right.connective] > precedence
        Rule = Callable[[BinaryExpression], bool]
        def subexpr(expr: ExpressionTree, omit_rule: Rule) -> str:
            # As an optimisation, use cleverness to omit the brackets for
            # certain cases of binary expressions. We can be dumb for other
            # (non-binary) expressions, because they'll omit the brackets for
            # use when we call bracketed().
            if isinstance(expr, BinaryExpression) and omit_rule(expr):
                return expr.source()
            else:
                return expr.bracketed()
        return ' '.join((
            subexpr(self.left, omit_left),
            self.connective,
            subexpr(self.right, omit_right),
        ))

@dataclass(frozen=True)
class UnaryExpression(ExpressionTree):
    subexpr: ExpressionTree
    operator: str
    def source(self) -> str:
        return self.operator + self.subexpr.bracketed()

@dataclass(frozen=True)
class AttrExpression(ExpressionTree):
    subexpr: ExpressionTree
    postfix: str
    def source(self) -> str:
        return self.subexpr.bracketed() + self.postfix
    def bracketed(self) -> str:
        # Attribute access (. operator) has highest precedence, so no brackets
        # needed.
        return self.source()

@dataclass(frozen=True)
class Atom(ExpressionTree):
    value: str
    def source(self) -> str:
        return self.value
    def bracketed(self) -> str:
        # Atoms by definition cannot be split by an adjacent operator of higher
        # precedence than whatever is in them. Therefore no brackets are
        # needed.
        return self.source()
