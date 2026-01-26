"""

Filtros personalizados para templates de Django.

"""

from django import template

register = template.Library()


@register.filter
def abs_value(value):

    """Retorna el valor absoluto de un número."""

    try:

        return abs(value)

    except (TypeError, ValueError):

        return value



@register.filter

def multiply(value, arg):

    """Multiplica un valor por el argumento."""

    try:

        return float(value) * float(arg)

    except (TypeError, ValueError):

        return value


@register.filter


def divide(value, arg):

    """Divide un valor por el argumento."""

    try:

        return float(value) / float(arg) if float(arg) != 0 else 0

    except (TypeError, ValueError):

        return value



@register.filter

def percentage(value, total):

    """Calcula el porcentaje de un valor respecto al total."""

    try:

        if float(total) == 0:

            return 0

        return (float(value) / float(total)) * 100

    except (TypeError, ValueError):

        return 0


@register.filter


def currency(value):

    """Formatea un valor como moneda."""

    try:

        return f"${float(value):,.2f}"

    except (TypeError, ValueError):

        return value


@register.filter
def subtract(value, arg):

    """Resta el argumento del valor."""

    try:

        return float(value) - float(arg)

    except (TypeError, ValueError):

        return value


@register.filter(name='add_class')
def add_class(field, css):

    """Agrega clases CSS a un widget de formulario en el template."""

    return field.as_widget(attrs={**field.field.widget.attrs, 'class': f"{field.field.widget.attrs.get('class', '')} {css}"})
