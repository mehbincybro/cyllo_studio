# -*- coding: utf-8 -*-
from lxml import etree
from odoo import api, models


class ResConfigSettings(models.TransientModel):
    """Extends res.config.settings model to customize form views."""
    _inherit = "res.config.settings"

    @api.model
    def get_views(self, views, options=None):
        """Override get_views method to customize form view.
        Parameters:
        - views (dict): Dictionary containing views information.
        - options (dict): Additional options for customization.
        Returns:
        - dict: Modified views dictionary.
        """
        ret_val = super().get_views(views, options)
        form_view = self.env["ir.ui.view"].browse(ret_val["views"]["form"]["id"])
        if not form_view.xml_id == "base.res_config_settings_view_form":
            return ret_val
        doc = etree.XML(ret_val["views"]["form"]["arch"])
        query = "//setting[field[@widget='upgrade_boolean']]"
        [elem.getparent().remove(elem) for elem in doc.xpath(query)]
        [setting.getparent().remove(setting) for setting in doc.xpath("//setting") if len(setting) == 0]
        [container.getparent().remove(container) for container in doc.xpath("//block") if len(container) == 0]
        ret_val["views"]["form"]["arch"] = etree.tostring(doc)
        return ret_val
