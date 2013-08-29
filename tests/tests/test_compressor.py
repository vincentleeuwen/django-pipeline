# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import base64
import os

try:
    from mock import patch
except ImportError:
    from unittest.mock import patch  # noqa

from django.test import TestCase

from pipeline.compressors import Compressor, TEMPLATE_FUNC, \
    SubProcessCompressor
from pipeline.compressors.yuglify import YuglifyCompressor

from tests.utils import _


class CompressorTest(TestCase):
    def setUp(self):
        self.maxDiff = None
        self.compressor = Compressor()

    def test_js_compressor_class(self):
        self.assertEqual(self.compressor.js_compressor, YuglifyCompressor)

    def test_css_compressor_class(self):
        self.assertEqual(self.compressor.css_compressor, YuglifyCompressor)

    def test_concatenate_and_rewrite(self):
        css = self.compressor.concatenate_and_rewrite([
            _('pipeline/css/first.css'),
            _('pipeline/css/second.css')
        ], 'css/screen.css')
        self.assertEqual(""".concat {\n  display: none;\n}\n\n.concatenate {\n  display: block;\n}\n""", css)

    def test_concatenate(self):
        js = self.compressor.concatenate([
            _('pipeline/js/first.js'),
            _('pipeline/js/second.js')
        ])
        self.assertEqual("""function concat() {\n  console.log(arguments);\n}\n\nfunction cat() {\n  console.log("hello world");\n}\n""", js)

    @patch.object(base64, 'b64encode')
    def test_encoded_content(self, mock):
        self.compressor.encoded_content(_('pipeline/images/arrow.png'))
        self.assertTrue(mock.called)
        mock.reset_mock()
        self.compressor.encoded_content(_('pipeline/images/arrow.png'))
        self.assertFalse(mock.called)

    def test_relative_path(self):
        relative_path = self.compressor.relative_path("images/sprite.png", 'css/screen.css')
        self.assertEqual(relative_path, '../images/sprite.png')

    def test_base_path(self):
        base_path = self.compressor.base_path([
            _('js/templates/form.jst'), _('js/templates/field.jst')
        ])
        self.assertEqual(base_path, _('js/templates'))

    def test_absolute_path(self):
        absolute_path = self.compressor.absolute_path('../../images/sprite.png',
            'css/plugins/')
        self.assertEqual(absolute_path, 'images/sprite.png')
        absolute_path = self.compressor.absolute_path('/images/sprite.png',
            'css/plugins/')
        self.assertEqual(absolute_path, '/images/sprite.png')

    def test_template_name(self):
        name = self.compressor.template_name('templates/photo/detail.jst',
            'templates/')
        self.assertEqual(name, 'photo_detail')
        name = self.compressor.template_name('templates/photo_edit.jst', '')
        self.assertEqual(name, 'photo_edit')
        name = self.compressor.template_name('templates\photo\detail.jst',
            'templates\\')
        self.assertEqual(name, 'photo_detail')

    def test_compile_templates(self):
        templates = self.compressor.compile_templates([_('pipeline/templates/photo/list.jst')])
        self.assertEqual(templates, """window.JST = window.JST || {};\n%s\nwindow.JST[\'list\'] = template(\'<div class="photo">\\n <img src="<%%= src %%>" />\\n <div class="caption">\\n  <%%= caption %%>\\n </div>\\n</div>\');\n""" % TEMPLATE_FUNC)
        templates = self.compressor.compile_templates([
            _('pipeline/templates/video/detail.jst'),
            _('pipeline/templates/photo/detail.jst')
        ])
        self.assertEqual(templates, """window.JST = window.JST || {};\n%s\nwindow.JST[\'video_detail\'] = template(\'<div class="video">\\n <video src="<%%= src %%>" />\\n <div class="caption">\\n  <%%= description %%>\\n </div>\\n</div>\');\nwindow.JST[\'photo_detail\'] = template(\'<div class="photo">\\n <img src="<%%= src %%>" />\\n <div class="caption">\\n  <%%= caption %%> by <%%= author %%>\\n </div>\\n</div>\');\n""" % TEMPLATE_FUNC)

    def test_embeddable(self):
        self.assertFalse(self.compressor.embeddable(_('pipeline/images/sprite.png'), None))
        self.assertFalse(self.compressor.embeddable(_('pipeline/images/arrow.png'), 'datauri'))
        self.assertTrue(self.compressor.embeddable(_('pipeline/images/embed/arrow.png'), 'datauri'))
        self.assertFalse(self.compressor.embeddable(_('pipeline/images/arrow.dat'), 'datauri'))

    def test_construct_asset_path(self):
        asset_path = self.compressor.construct_asset_path("../../images/sprite.png",
            "css/plugins/gallery.css", "css/gallery.css")
        self.assertEqual(asset_path, "../images/sprite.png")
        asset_path = self.compressor.construct_asset_path("/images/sprite.png",
            "css/plugins/gallery.css", "css/gallery.css")
        self.assertEqual(asset_path, "/images/sprite.png")

    def test_url_rewrite(self):
        output = self.compressor.concatenate_and_rewrite([
            _('pipeline/css/urls.css'),
        ], 'css/screen.css')
        self.assertEqual("""@font-face {
  font-family: 'Pipeline';
  src: url(../pipeline/fonts/pipeline.eot);
  src: url(../pipeline/fonts/pipeline.eot?#iefix) format('embedded-opentype');
  src: local('☺'), url(../pipeline/fonts/pipeline.woff) format('woff'), url(../pipeline/fonts/pipeline.ttf) format('truetype'), url(../pipeline/fonts/pipeline.svg#IyfZbseF) format('svg');
  font-weight: normal;
  font-style: normal;
}
.relative-url {
  background-image: url(../pipeline/images/sprite-buttons.png);
}
.relative-url-querystring {
  background-image: url(../pipeline/images/sprite-buttons.png?v=1.0#foo=bar);
}
.absolute-url {
  background-image: url(/images/sprite-buttons.png);
}
.absolute-full-url {
  background-image: url(http://localhost/images/sprite-buttons.png);
}
.no-protocol-url {
  background-image: url(//images/sprite-buttons.png);
}""", output)

    def test_compressor_subprocess_unicode(self):
        tests_path = os.path.dirname(os.path.dirname(__file__))
        output = SubProcessCompressor(False).execute_command(
            '/usr/bin/env cat',
            open(tests_path + '/assets/css/unicode.css').read())
        self.assertEqual(""".some_class {
  // Some unicode
  content: "áéíóú";
}
""", output)
