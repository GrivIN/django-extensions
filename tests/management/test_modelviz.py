# -*- coding: utf-8 -*-
from unittest import skipIf, skipUnless, skip
import six
from mock import patch, mock_open
from django.db import models
from django.test import SimpleTestCase
from django_extensions.management.modelviz import (
    ModelGraph,
    parse_file_or_list,
    use_model,
    generate_graph_data,
)
if six.PY3:
    BUILTIN_OPEN = 'builtins.open'
else:
    BUILTIN_OPEN = '__builtin__.open'


class ModelVizTests(SimpleTestCase):
    @patch('os.path.isfile')
    @patch(BUILTIN_OPEN, mock_open(read_data='foo\nbar'))
    def test_parse_file_or_list(self, isfile_mock):
        isfile_mock.return_value = True
        self.assertEqual(
            parse_file_or_list(),
            []
        )
        self.assertEqual(
            parse_file_or_list('foo,bar'),
            ['foo', 'bar']
        )
        self.assertEqual(
            parse_file_or_list('foobar.txt'),
            ['foo', 'bar']
        )

    def test_use_model(self):
        include_models = [
            'NoWildcardInclude',
            'Wildcard*InsideInclude',
            '*WildcardPrefixInclude',
            'WildcardSuffixInclude*',
            '*WildcardBothInclude*'
        ]
        exclude_models = [
            'NoWildcardExclude',
            'Wildcard*InsideExclude',
            '*WildcardPrefixExclude',
            'WildcardSuffixExclude*',
            '*WildcardBothExclude*'
        ]
        # Any model name should be used if neither include or exclude
        # are defined.
        self.assertTrue(
            ModelGraph(
                []
            ).use_model(
                'SomeModel'
            )
        )
        # Any model name should be allowed if `*` is in `include_models`.
        self.assertTrue(
            ModelGraph(
                [],
                include_models=['OtherModel', '*', 'Wildcard*Model']
            ).use_model(
                'SomeModel'
            )
        )
        # No model name should be allowed if `*` is in `exclude_models`.
        self.assertFalse(
            ModelGraph(
                [],
                exclude_models=['OtherModel', '*', 'Wildcard*Model']
            ).use_model(
                'SomeModel'
            )
        )
        # Some tests with the `exclude_models` and `include_models` defined above.
        models_graph = ModelGraph(
            [],
            include_models=include_models,
            exclude_models=exclude_models
        )
        self.assertTrue(models_graph.use_model(
            'NoWildcardInclude',
        ))
        self.assertTrue(models_graph.use_model(
            'WildcardSomewhereInsideInclude',
        ))
        self.assertTrue(models_graph.use_model(
            'MyWildcardPrefixInclude',
        ))
        self.assertTrue(models_graph.use_model(
            'WildcardSuffixIncludeModel',
        ))
        self.assertTrue(models_graph.use_model(
            'MyWildcardBothIncludeModel',
        ))
        # FIXME: if both, include-models and exclude-models are given,
        #        what should be done if model is in none of them?
        self.assertFalse(models_graph.use_model(
            'SomeModel',
        ))
        self.assertFalse(models_graph.use_model(
            'NoWildcardExclude',
        ))
        self.assertFalse(models_graph.use_model(
            'WildcardSomewhereInsideExclude',
        ))
        self.assertFalse(models_graph.use_model(
            'MyWildcardPrefixExclude',
        ))
        self.assertFalse(models_graph.use_model(
            'WildcardSuffixExcludeModel',
        ))
        self.assertFalse(models_graph.use_model(
            'MyWildcardBothExcludeModel',
        ))

    def test_skip_field(self):
        exclude_columns = [
            'SomeField',
            'SomeVerboseField'
        ]
        models_graph = ModelGraph(
            []
        )
        self.assertFalse(models_graph.skip_field(
            models.Field(name='SomeField'),
        ))

        models_graph = ModelGraph(
            [],
            exclude_columns=exclude_columns
        )
        self.assertTrue(
            models_graph.skip_field(models.Field(name='SomeField')),
        )

        models_graph = ModelGraph(
            [],
            verbose_names=True,
            exclude_columns=exclude_columns
        )
        self.assertFalse(models_graph.skip_field(
            models.Field(name='VerboseField'),
        ))
        self.assertTrue(models_graph.skip_field(
            models.Field(verbose_name='SomeVerboseField'),
        ))

    def test_get_appmodel_attributes(self):
        class TestModel(models.Model):
            name = models.CharField()
            parent = models.ForeignKey('self')

            class Meta:
                app_label = 'test'

        models_graph = ModelGraph(
            []
        )
        attributes = models_graph.get_appmodel_attributes(TestModel)
        self.assertIn('name', [a.verbose_name for a in attributes])
        self.assertIn('parent', [a.verbose_name for a in attributes])

        models_graph = ModelGraph(
            [],
            relations_as_fields=False
        )
        attributes = models_graph.get_appmodel_attributes(TestModel)
        self.assertIn('name', [a.verbose_name for a in attributes])
        self.assertNotIn('parent', [a.verbose_name for a in attributes])

    def test_get_appmodel_abstracts(self):
        class TestAbstractModel(models.Model):
            family = models.CharField()

            class Meta:
                app_label = 'test'
                abstract = True

        class TestModel(TestAbstractModel):
            name = models.CharField()

            class Meta:
                app_label = 'test'

        models_graph = ModelGraph(
            [],
            relations_as_fields=False
        )
        abstracts = models_graph.get_appmodel_abstracts(TestModel)
        self.assertEqual(abstracts, ['TestAbstractModel'])

    def test_get_abstract_models(self):
        class TestAbstractModel(models.Model):
            family = models.CharField()

            class Meta:
                app_label = 'test'
                abstract = True

        class TestModelOne(TestAbstractModel):
            name = models.CharField()

            class Meta:
                app_label = 'test'

        class TestModelTwo(TestAbstractModel):
            name = models.CharField()

            class Meta:
                app_label = 'test'

        models_graph = ModelGraph(
            [],
            relations_as_fields=False
        )
        abstracts = models_graph.get_abstract_models(
            [TestModelOne, TestModelTwo])
        self.assertEqual(abstracts, [TestAbstractModel])

    def test_get_bases_abstract_fields(self):
        class TestAbstractModel(models.Model):
            family = models.CharField()

            class Meta:
                app_label = 'test'
                abstract = True

        class TestModelOne(TestAbstractModel):
            name = models.CharField()

            class Meta:
                app_label = 'test'

        class TestModelTwo(TestAbstractModel):
            name = models.CharField()

            class Meta:
                app_label = 'test'

        models_graph = ModelGraph(
            [],
        )
        abstracts = models_graph.get_bases_abstract_fields(
            TestModelOne
        )
        self.assertEqual(
            abstracts,
            [TestAbstractModel._meta.get_field('family')]
        )

    def test_get_inheritance_context_abstract(self):
        class TestAbstractModel(models.Model):
            family = models.CharField()

            class Meta:
                app_label = 'test'
                abstract = True

        class TestModelOne(TestAbstractModel):
            name = models.CharField()

            class Meta:
                app_label = 'test'

        models_graph = ModelGraph(
            [],
        )
        abstracts = models_graph.get_inheritance_context(
            TestModelOne, TestAbstractModel
        )
        self.assertEqual(
            abstracts['label'],
            "abstract\\ninheritance"
        )

    def test_get_inheritance_context_proxy(self):
        class TestAbstractModel(models.Model):
            family = models.CharField()

            class Meta:
                app_label = 'test'

        class TestModelOne(TestAbstractModel):

            class Meta:
                app_label = 'test'
                proxy = True

        models_graph = ModelGraph(
            [],
        )
        abstracts = models_graph.get_inheritance_context(
            TestModelOne, TestAbstractModel
        )
        self.assertEqual(
            abstracts['label'],
            "proxy\\ninheritance"
        )

    def test_get_inheritance_context(self):
        class TestAbstractModel(models.Model):
            family = models.CharField()

            class Meta:
                app_label = 'test'

        class TestModelOne(TestAbstractModel):

            class Meta:
                app_label = 'test'

        models_graph = ModelGraph(
            [],
        )
        abstracts = models_graph.get_inheritance_context(
            TestModelOne, TestAbstractModel
        )
        self.assertEqual(
            abstracts['label'],
            "multi-table\\ninheritance"
        )

    def test_add_attributes(self):
        field = models.Field(name='some field', verbose_name='some verbose field')

        models_graph = ModelGraph(
            [],
            verbose_names=True
        )
        attributes = models_graph.add_attributes(field, abstract_fields=[])
        self.assertIn('name', attributes)
        self.assertIn('label', attributes)
        self.assertEqual(attributes['label'], b'Some verbose field')
        self.assertEqual(attributes['type'], 'Field')

        models_graph = ModelGraph(
            [],
            verbose_names=False
        )
        attributes = models_graph.add_attributes(field, abstract_fields=[])
        self.assertEqual(attributes['label'], 'some field')

    def test_add_attributes_fk(self):
        class TestModel(models.Model):
            name = models.CharField()
            parent = models.ForeignKey(
                'self', verbose_name='parent verbose field')

            class Meta:
                app_label = 'test'

        models_graph = ModelGraph(
            [],
            verbose_names=False
        )
        attributes = models_graph.add_attributes(
            TestModel._meta.get_field('parent'), abstract_fields=[])
        self.assertEqual(attributes['label'], 'parent')
        self.assertEqual(attributes['type'], 'ForeignKey (id)')

    def test_process_attributes(self):
        class TestModel(models.Model):
            name = models.CharField()
            parent = models.ForeignKey(
                'self', verbose_name='parent verbose field')

            class Meta:
                app_label = 'test'

        models_graph = ModelGraph(
            [],
            verbose_names=False
        )
        attributes = models_graph.process_attributes(
            TestModel._meta.get_field('parent'),
            {'fields': []},
            TestModel._meta.get_field('id'),
            abstract_fields=[]
        )
        self.assertIn('fields', attributes)
        self.assertEqual(len(attributes['fields']), 1)
        self.assertIn('label', attributes['fields'][0])
        self.assertEqual(attributes['fields'][0]['label'], 'parent')

        attributes = models_graph.process_attributes(
            TestModel._meta.get_field('id'),
            {'fields': []},
            TestModel._meta.get_field('id'),
            abstract_fields=[]
        )
        self.assertEqual(attributes, {'fields': []})

    def test_add_relation(self):
        class ParentModel(models.Model):
            name = models.CharField()

            class Meta:
                app_label = 'test'

        class ChildModel(models.Model):
            name = models.CharField()
            father = models.ForeignKey(
                ParentModel, verbose_name='father verbose field')
            mother = models.ForeignKey(
                'ParentModel', verbose_name='mother verbose field')
            sibling = models.ForeignKey(
                'self', verbose_name='sibling verbose field')

            class Meta:
                app_label = 'test'

        models_graph = ModelGraph(
            [],
            verbose_names=False
        )
        attributes = models_graph.add_relation(
            ChildModel._meta.get_field('father'),
            {'relations': []},
            extras=''
        )
        self.assertIn('target', attributes)
        self.assertEqual(attributes['target'], 'ParentModel')
        # self.assertEqual(attributes['label'], b"father (childmodel)")

        models_graph = ModelGraph(
            [],
            verbose_names=True
        )
        attributes = models_graph.add_relation(
            ChildModel._meta.get_field('father'),
            {'relations': []},
            extras=''
        )
        self.assertIn('target', attributes)
        self.assertEqual(attributes['target'], 'ParentModel')
        # self.assertEqual(
        #     attributes['label'], b"Father verbose field (Childmodel)")

        attributes = models_graph.add_relation(
            ChildModel._meta.get_field('mother'),
            {'relations': []},
            extras=''
        )
        self.assertIn('target', attributes)
        self.assertEqual(attributes['target'], 'ParentModel')

        attributes = models_graph.add_relation(
            ChildModel._meta.get_field('sibling'),
            {'relations': []},
            extras=''
        )
        self.assertIn('target', attributes)
        self.assertEqual(attributes['target'], 'ChildModel')

    def test_get_appmodel_context(self):
        class TestModel(models.Model):
            name = models.CharField()
            parent = models.ForeignKey(
                'self', verbose_name='parent verbose field')

            class Meta:
                app_label = 'test'
                verbose_name = 'test verbose model'

        models_graph = ModelGraph(
            [],
            verbose_names=False
        )
        context = models_graph.get_appmodel_context(
            TestModel, appmodel_abstracts=[])
        self.assertIn('fields', context)
        self.assertIn('app_name', context)
        self.assertIn('name', context)
        self.assertIn('label', context)
        self.assertIn('abstracts', context)
        self.assertIn('relations', context)
        self.assertEqual(context['label'], context['name'])
        self.assertEqual(context['label'], 'TestModel')

        models_graph = ModelGraph(
            [],
            verbose_names=True
        )
        context = models_graph.get_appmodel_context(
            TestModel, appmodel_abstracts=[])
        self.assertIn('fields', context)
        self.assertIn('app_name', context)
        self.assertIn('name', context)
        self.assertIn('label', context)
        self.assertIn('abstracts', context)
        self.assertIn('relations', context)
        self.assertEqual(context['label'], b'test verbose model')


class LagencyModelVizTests(SimpleTestCase):
    @skip
    def test_use_model_lagency_method(self):
        include_models = [
            'NoWildcardInclude',
            'Wildcard*InsideInclude',
            '*WildcardPrefixInclude',
            'WildcardSuffixInclude*',
            '*WildcardBothInclude*'
        ]
        exclude_models = [
            'NoWildcardExclude',
            'Wildcard*InsideExclude',
            '*WildcardPrefixExclude',
            'WildcardSuffixExclude*',
            '*WildcardBothExclude*'
        ]
        # Any model name should be used if neither include or exclude
        # are defined.
        self.assertTrue(use_model(
            'SomeModel',
            None,
            None
        ))
        # Any model name should be allowed if `*` is in `include_models`.
        self.assertTrue(use_model(
            'SomeModel',
            ['OtherModel', '*', 'Wildcard*Model'],
            None
        ))
        # No model name should be allowed if `*` is in `exclude_models`.
        self.assertFalse(use_model(
            'SomeModel',
            None,
            ['OtherModel', '*', 'Wildcard*Model']
        ))
        # Some tests with the `include_models` defined above.
        self.assertFalse(use_model(
            'SomeModel',
            include_models,
            None
        ))
        self.assertTrue(use_model(
            'NoWildcardInclude',
            include_models,
            None
        ))
        self.assertTrue(use_model(
            'WildcardSomewhereInsideInclude',
            include_models,
            None
        ))
        self.assertTrue(use_model(
            'MyWildcardPrefixInclude',
            include_models,
            None
        ))
        self.assertTrue(use_model(
            'WildcardSuffixIncludeModel',
            include_models,
            None
        ))
        self.assertTrue(use_model(
            'MyWildcardBothIncludeModel',
            include_models,
            None
        ))
        # Some tests with the `exclude_models` defined above.
        self.assertTrue(use_model(
            'SomeModel',
            None,
            exclude_models
        ))
        self.assertFalse(use_model(
            'NoWildcardExclude',
            None,
            exclude_models
        ))
        self.assertFalse(use_model(
            'WildcardSomewhereInsideExclude',
            None,
            exclude_models
        ))
        self.assertFalse(use_model(
            'MyWildcardPrefixExclude',
            None,
            exclude_models
        ))
        self.assertFalse(use_model(
            'WildcardSuffixExcludeModel',
            None,
            exclude_models
        ))
        self.assertFalse(use_model(
            'MyWildcardBothExcludeModel',
            None,
            exclude_models
        ))

    @skip
    def test_no_models_dot_py_lagency_method(self):
        data = generate_graph_data(['testapp_with_no_models_file'])
        self.assertEqual(len(data['graphs']), 1)

        model_name = data['graphs'][0]['models'][0]['name']
        self.assertEqual(model_name, 'TeslaCar')

    @skip
    @skipIf(six.PY3, 'FIXME Python 3 renders labels funny, see below')
    def test_generate_graph_data_can_render_label_lagency_method(self):
        app_labels = ['auth']
        data = generate_graph_data(app_labels)

        models = data['graphs'][0]['models']
        user_data = [x for x in models if x['name'] == 'User'][0]
        relation_labels = [x['label'] for x in user_data['relations']]
        self.assertIn("groups (user)", relation_labels)

    @skip
    @skipUnless(six.PY3, 'DELETEME Python 3 should render the same as Python 2')
    def test_generate_graph_data_formats_labels_as_bytes_lagency_method(self):
        app_labels = ['auth']
        data = generate_graph_data(app_labels)

        models = data['graphs'][0]['models']
        user_data = [x for x in models if x['name'] == 'User'][0]
        relation_labels = [x['label'] for x in user_data['relations']]
        self.assertIn("groups (b'user')", relation_labels)
