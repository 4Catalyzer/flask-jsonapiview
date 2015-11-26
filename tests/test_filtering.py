from flask.ext.resty import Api, filter_function, Filtering, GenericModelView
from marshmallow import fields, Schema
import operator
import pytest
from sqlalchemy import Column, Integer, String

import helpers

# -----------------------------------------------------------------------------


@pytest.yield_fixture
def models(db):
    class Widget(db.Model):
        __tablename__ = 'widgets'

        id = Column(Integer, primary_key=True)
        color = Column(String)
        size = Column(Integer)

    db.create_all()

    yield {
        'widget': Widget,
    }

    db.drop_all()


@pytest.fixture
def schemas():
    class WidgetSchema(Schema):
        id = fields.Integer(as_string=True)
        color = fields.String()
        size = fields.Integer()

    return {
        'widget': WidgetSchema(),
    }


@pytest.fixture
def filter_fields():
    @filter_function(fields.Boolean())
    def filter_size_is_odd(model, value):
        return model.size % 2 == int(value)

    return {
        'size_is_odd': filter_size_is_odd
    }


@pytest.fixture(autouse=True)
def routes(app, models, schemas, filter_fields):
    class WidgetListView(GenericModelView):
        model = models['widget']
        schema = schemas['widget']

        filtering = Filtering(
            color=operator.eq,
            size_min=('size', operator.ge),
            size_divides=('size', lambda size, value: size % value == 0),
            size_is_odd=filter_fields['size_is_odd'],
        )

        def get(self):
            return self.list()

    api = Api(app, '/api')
    api.add_resource('/widgets', WidgetListView)


@pytest.fixture(autouse=True)
def data(db, models):
    def create_widget(color, size):
        widget = models['widget']()
        widget.color = color
        widget.size = size
        return widget

    db.session.add_all((
        create_widget('red', 1),
        create_widget('green', 2),
        create_widget('blue', 3),
        create_widget('red', 6),
    ))
    db.session.commit()


# -----------------------------------------------------------------------------


def test_eq(client):
    response = client.get('/api/widgets?color=red')
    assert helpers.get_data(response) == [
        {
            'id': '1',
            'color': 'red',
            'size': 1,
        },
        {
            'id': '4',
            'color': 'red',
            'size': 6,
        },
    ]


def test_eq_many(client):
    response = client.get('/api/widgets?color=green,blue')
    assert helpers.get_data(response) == [
        {
            'id': '2',
            'color': 'green',
            'size': 2,
        },
        {
            'id': '3',
            'color': 'blue',
            'size': 3,
        },
    ]


def test_ge(client):
    response = client.get('/api/widgets?size_min=3')
    assert helpers.get_data(response) == [
        {
            'id': '3',
            'color': 'blue',
            'size': 3,
        },
        {
            'id': '4',
            'color': 'red',
            'size': 6,
        },
    ]


def test_custom_operator(client):
    response = client.get('/api/widgets?size_divides=2')
    assert helpers.get_data(response) == [
        {
            'id': '2',
            'color': 'green',
            'size': 2,
        },
        {
            'id': '4',
            'color': 'red',
            'size': 6,
        },
    ]


def test_filter_field(client):
    response = client.get('/api/widgets?size_is_odd=true')
    assert helpers.get_data(response) == [
        {
            'id': '1',
            'color': 'red',
            'size': 1,
        },
        {
            'id': '3',
            'color': 'blue',
            'size': 3,
        },
    ]


def test_error(client):
    response = client.get('/api/widgets?size_min=foo')
    assert response.status_code == 400

    errors = helpers.get_errors(response)
    for error in errors:
        assert error.pop('detail', None) is not None
    assert errors == [{
        'code': 'invalid_filter',
        'source': {'parameter': 'size_min'},
    }]