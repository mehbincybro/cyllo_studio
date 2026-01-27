# -*- coding: utf-8 -*-
import werkzeug
from odoo.addons.website_blog.controllers.main import WebsiteBlog
from odoo import http, tools
from odoo.addons.http_routing.models.ir_http import slug, unslug
from odoo.addons.website.controllers.main import QueryURL
from odoo.http import request


class WebsiteBlogInherit(WebsiteBlog):
    """
        Extended class for managing blog-related routes and views on the
        website.
    """
    def blog(self, blog=None, tag=None, page=1, search=None, **opt):
        """
        Route for displaying blog-related pages on the website.
        """
        Blog = request.env['blog.blog']
        blogs = tools.lazy(
            lambda: Blog.search(['|', ('website_ids', '=', request.website.id), ('website_ids', '=', False)],
                                order="create_date asc, id asc"))
        if not blog and len(blogs) == 1:
            url = QueryURL('/blog/%s' % slug(blogs[0]), search=search, **opt)()
            return request.redirect(url, code=302)
        date_begin, date_end = opt.get('date_begin'), opt.get('date_end')
        if tag and request.httprequest.method == 'GET':
            # redirect get tag-1,tag-2 -> get tag-1
            tags = tag.split(',')
            if len(tags) > 1:
                url = QueryURL('' if blog else '/blog', ['blog', 'tag'], blog=blog, tag=tags[0], date_begin=date_begin,
                               date_end=date_end, search=search)()
                return request.redirect(url, code=302)
        values = self._prepare_blog_values(blogs=blogs, blog=blog, tags=tag, page=page, search=search, **opt)
        # in case of a redirection need by `_prepare_blog_values` we follow it
        if isinstance(values, werkzeug.wrappers.Response):
            return values
        if blog:
            values['main_object'] = blog
        values['blog_url'] = QueryURL('/blog', ['blog', 'tag'], blog=blog, tag=tag, date_begin=date_begin,
                                      date_end=date_end, search=search)
        return request.render("website_blog.blog_post_short", values)
