# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import re
import logging

from io import StringIO
from lxml import etree

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools.view_validation import valid_view

_logger = logging.getLogger(__name__)


class View(models.Model):
    """Extend ir.ui.view with Studio-specific logic."""
    _inherit = 'ir.ui.view'

    is_studio = fields.Boolean(string='Studio Field', default=False,
                               help="View created through Studio", ondelete='cascade')

    def _postprocess_access_rights(self, tree):
        """
        Apply group restrictions: elements with a 'groups' attribute should
        be removed from the view to people who are not members.

        Compute and set on node access rights based on view type. Specific
        views can add additional specific rights like creating columns for
        many2one-based grouping views.
        """
        # Check if 'studio' is not in the debug session
        studio = request.session.studio
        is_not_studio_debug = '1' not in studio if studio else True
        # Check if the user is not part of the 'base.group_erp_manager' group
        is_not_erp_manager = not request.env.user.has_group('base.group_erp_manager')

        if is_not_studio_debug or is_not_erp_manager:
            return super()._postprocess_access_rights(tree)
        for node in tree.xpath('//*[@groups]'):
            attrib_groups = node.attrib.pop('groups')
            if node.tag == 't' and node.get('postprocess_added'):
                for child in reversed(node):
                    child_group = child.get("groups", "")
                    combined_groups = set(child_group.split(",") + attrib_groups.split(","))
                    combined_groups_str = ",".join(filter(None, combined_groups))
                    child.set("default_groups", attrib_groups)
                    node.addnext(child)
                node.getparent().remove(node)
            else:
                node.set("groups", attrib_groups)

        arch = etree.tostring(tree, encoding="unicode").replace(
            '\t', '')

        parser = etree.XMLParser()
        arch_tree = etree.parse(StringIO(arch), parser)
        elements = arch_tree.xpath("//*")
        for element in elements:
            xpath = arch_tree.getpath(element)
            for path in tree.xpath(f'//{xpath}'):
                path.set('cy-xpath', xpath)
                if tree.tag == "kanban" or (tree.tag == "form" and any(
                        parent.tag == "kanban" for parent in path.iterancestors())):
                    if path.get('t-if') or path.get('t-elif') or path.get('t-else'):
                        path.set('data-restrict', '1')
                    if path.tag == "div":
                        if 'ribbon' in path.get('class', ''):
                            path.set('class', f"{path.get('class', '').strip()}")
                            path.set('data-ribbon', '1')

                            for attr in ['invisible', 't-if', 't-elif', 't-else']:
                                val = path.attrib.pop(attr, None)
                                if val is not None:
                                    path.set(f"data-{attr}", val)

                            for child in path.iter():
                                for attr in ['invisible', 't-if', 't-elif', 't-else']:
                                    val = child.attrib.pop(attr, None)
                                    if val is not None:
                                        child.set(f"data-{attr}", val)
                        else:
                            path.set('data-drag', '1')

        if tree.tag == 'search':
            filters_without_context = tree.xpath('//filter[not(@context)]')
            filters_with_context = tree.xpath('//filter[@context]')
            last_filter_without_context = filters_without_context[-1] if filters_without_context else None
            last_filter_with_context = filters_with_context[-1] if filters_with_context else None
            new_element = etree.Element("studio")
            if last_filter_without_context is not None:
                new_element.set('filter', last_filter_without_context.get('cy-xpath'))
            if last_filter_with_context is not None:
                new_element.set('group_by', last_filter_with_context.get('cy-xpath'))

            tree.append(new_element)
        elif tree.tag == 'form':
            header = tree.xpath('//header')
            sheet = tree.xpath(".//sheet")
            if not sheet:
                new_sheet = etree.Element("sheet")
                new_sheet.set('cy-xpath', '/form/sheet')
                new_sheet.set('sheet', 'true')
                children_to_move = [child for child in tree if child.getparent() is tree and child.tag != "header"]
                for child in children_to_move:
                    new_sheet.append(child)
                tree.insert(0, new_sheet)
            if not header:
                new_header = etree.Element("header")
                new_header.set('cy-xpath', '/form/header')
                new_header.set('studio-header', f'/form/{tree[0].tag if tree else ""}')
                tree.insert(0, new_header)
            status_bar = tree.xpath('//header/field[@widget="statusbar"]') or tree.xpath(
                '//header/field[@widget="statusbar_duration"]')
            if status_bar:
                header = tree.xpath('//header')
                header[0].set('status-bar', 'true')
            avatar = tree.xpath('//sheet//field[contains(@class, "oe_avatar") and @widget="image"]')
            if avatar:
                sheet = tree.xpath('./sheet')
                sheet[0].set('avatar', 'true')

        for node in tree.xpath('//*[@groups]'):
            attrib_groups = node.attrib.get('groups')
            if node.tag == 't' and (not node.attrib or (len(node.attrib) == 2 and 'groups' in node.attrib)):
                for child in reversed(node):
                    node.addnext(child)
                node.getparent().remove(node)
                continue
            if attrib_groups and not self.user_has_groups(attrib_groups):
                if tree.tag in ['tree', 'kanban'] and request.session.get('invisible', 'False') != "False":
                    node.set('striped', 'true')
                elif tree.tag == 'form' and request.session.get('invisible', 'False') != "False":
                    if node.tag == 'div' and 'class' in node.attrib and 'o_row' in node.attrib['class'].split():
                        node.set('class', f"{node.attrib['class']} cy-studio-striped")
                    else:
                        node.set('striped', 'true')
                elif tree.tag == 'search' and request.session.get('show_invisible_search'):
                    node.set('striped', 'true')
                elif tree.tag == 'search' and node.tag == 'searchpanel':
                    node.set('isInvisible', 'true')
                else:
                    node.getparent().remove(node)
                    continue
                # ToDO Need to find better way for handle default group fields.
                if 'model_access_rights' in node.attrib:
                    node.getparent().remove(node)

        if tree.tag == 'form':
            button_box = tree.findall(".//div[@class='oe_button_box']")
            button_box_child = []
            for box in button_box:
                child = box.findall(".//button")
                if child:
                    button_box_child.append(child)
            if not button_box_child:
                new_button_box = etree.Element("div")
                new_button_box.set('cy-xpath', '//form/sheet/div[@class="oe_button_box"]')
                new_button_box.set('class', 'oe_button_box')
                new_button_box.set('name', 'button_box')
                child_div = etree.Element("div")
                child_div.set('class', 'button-box-container')
                new_button_box.append(child_div)
                sheet = tree.xpath('./sheet')
                form = tree.xpath('./form')
                if sheet:
                    sheet[0].insert(0, new_button_box)
        base_model = tree.get('model_access_rights')
        for node in tree.xpath('//*[@model_access_rights]'):
            model = self.env[node.attrib.pop('model_access_rights')]
            if node.tag == 'field':
                can_create = model.check_access_rights('create',
                                                       raise_exception=False)
                can_write = model.check_access_rights('write',
                                                      raise_exception=False)
                node.set('can_create', str(bool(can_create)))
                node.set('can_write', str(bool(can_write)))
            else:
                is_base_model = base_model == model._name
                for action, operation in (
                        ('create', 'create'), ('delete', 'unlink'),
                        ('edit', 'write')):
                    if not node.get(action) and not model.check_access_rights(
                            operation, raise_exception=False):
                        node.set(action, 'False')
                if node.tag == 'kanban':
                    group_by_name = node.get('default_group_by')
                    group_by_field = model._fields.get(group_by_name)
                    if group_by_field and group_by_field.type == 'many2one':
                        group_by_model = model.env[group_by_field.comodel_name]
                        for action, operation in (
                                ('group_create', 'create'),
                                ('group_delete', 'unlink'),
                                ('group_edit', 'write')):
                            if not node.get(
                                    action) and not group_by_model.check_access_rights(
                                operation, raise_exception=False):
                                node.set(action, 'False')

        return tree

    def _get_x2many_missing_view_archs(self, field, field_node, node_info):
        """Add model and view info for x2many fields."""
        result = super()._get_x2many_missing_view_archs(field, field_node, node_info)
        field_node.set('model', f'{field.comodel_name}')
        for _, view in result:
            field_node.set(f'{view.type}', f'{view.id}')
        return result

    # Overriding this method to fix the issue in the tree view drag and drop,adding help parameter
    @api.constrains('arch_db')
    def _check_xml(self):
        """Validate Studio views and ensure XML correctness."""
        # Sanity checks: the view should not break anything upon rendering!
        # Any exception raised below will cause a transaction rollback.
        partial_validation = self.env.context.get('ir_ui_view_partial_validation')
        self = self.with_context(validate_view_ids=(self._ids if partial_validation else True))
        for view in self:
            try:
                # verify the view is valid xml and that the inheritance resolves
                if view.inherit_id:
                    view_arch = etree.fromstring(view.arch)
                    view._valid_inheritance(view_arch)
                combined_arch = view._get_combined_arch()
                if view.type == 'qweb':
                    continue
            except (etree.ParseError, ValueError) as e:
                err = ValidationError(_(
                    "Error while parsing or validating view:\n\n%(error)s",
                    error=tools.ustr(e),
                    view=view.key or view.id,
                )).with_traceback(e.__traceback__)
                err.context = getattr(e, 'context', None)
                raise err from None
            try:
                # verify that all fields used are valid, etc.
                view._validate_view(combined_arch, view.model)
                combined_archs = [combined_arch]

                if combined_arch.xpath('//*[@attrs]') or combined_arch.xpath('//*[@states]'):
                    view_name = f'{view.name} ({view.xml_id})' if view.xml_id else view.name
                    err = ValidationError(
                        _('Since 17.0, the "attrs" and "states" attributes are no longer used.\nView: %(name)s in %(file)s',
                          name=view_name, file=view.arch_fs
                          ))
                    err.context = {'name': 'invalid view'}
                    raise err

                if combined_archs[0].tag == 'data':
                    # A <data> element is a wrapper for multiple root nodes
                    combined_archs = combined_archs[0]
                for view_arch in combined_archs:

                    if view_arch.tag == "activity":
                        # Remove the 'delete' attribute from the root if it exists
                        if view_arch.attrib.get('delete'):
                            del view_arch.attrib['delete']

                    for node in view_arch.xpath('//*[@__validate__]'):
                        del node.attrib['__validate__']

                    check = valid_view(view_arch, env=self.env, model=view.model)
                    if not check and view.type != 'tree':
                        view_name = f'{view.name} ({view.xml_id})' if view.xml_id else view.name
                        raise ValidationError(_(
                            'Invalid view %(name)s definition in %(file)s',
                            name=view_name, file=view.arch_fs
                        ))
            except ValueError as e:
                if hasattr(e, 'context'):
                    lines = etree.tostring(combined_arch, encoding='unicode').splitlines(keepends=True)
                    fivelines = "".join(lines[max(0, e.context["line"] - 3):e.context["line"] + 2])
                    err = ValidationError(_(
                        "Error while validating view near:\n\n%(fivelines)s\n%(error)s",
                        fivelines=fivelines, error=tools.ustr(e),
                    ))
                    err.context = e.context
                    raise err.with_traceback(e.__traceback__) from None
                else:
                    err = ValidationError(_(
                        "Error while validating view (%(view)s):\n\n%(error)s", view=self.key or self.id,
                        error=tools.ustr(e.__context__),
                    ))
                    err.context = {'name': 'invalid view'}
                    raise err.with_traceback(e.__context__.__traceback__) from None
        return True


class Model(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        """
        Hide Chatter Views, Tabs, Buttons, Fields, Duplicate option, Filters,
        Groups and set readonly the user profile(preference) based on the
        access manager
         """

        views = ["tree", "form", "kanban", 'calendar', 'activity', 'hierarchy', 'graph', 'pivot']

        if type(self).__name__ == 'ir.model.access' or type(self).__name__ == 'ir.rule':
            views.remove('tree')
        if type(self).__name__ == 'mail.template':
            views.remove('kanban')
            views.remove("form")
        if type(self).__name__ == 'ir.actions.report':
            views.remove('kanban')

        result = super().get_view(view_id, view_type, **options)
        studio = request.session.studio
        is_not_studio_debug = '1' not in studio if studio else True
        is_not_erp_manager = not request.env.user.has_group('base.group_erp_manager')

        if is_not_studio_debug or is_not_erp_manager:
            return result
        if view_type in views:
            xml_string = re.sub(r'\s+js_class="[^"]*"', '', result['arch'])
            xml_string = re.sub(r'(<group[^>]*?)\s+col="4"', r'\1', xml_string)
            xml_string = re.sub(r'<t[^>]*groups="stock.group_stock_manager"[^>]*>.*?</t>', '', xml_string,
                                flags=re.DOTALL)

            result['arch'] = xml_string
        return result

    # studio report modification

    @api.model
    def get_iframe_rendered_template(self, template_name, max_depth=8):
        """
        Render a full template for iframe editing:
        - Expands internal t-calls.
        - Skips global web.* / report.* templates.
        - Preserves <t> nodes (does not solve t directives).
        - Returns HTML string ready to embed in <iframe srcdoc>.
        """
        cache = {}
        html_body = self._expand_template_for_iframe(template_name, depth=0, max_depth=max_depth,
                                                     cache=cache)

        html_container = self.env['ir.qweb']._render('web.html_container', {})
        container_doc = html.fromstring(html_container)

        # adding medium editor to head
        head_el = container_doc.xpath('//head')[0]
        head_content = """<data><style>
                                    .snippet {
                                        padding: 8px;
                                        margin: 4px;
                                        border: 1px solid #888;
                                        border-radius: 10px;
                                        background: #f8f8f8;
                                        cursor: grab;
                                    }
                                    .medium-editor-element::selection {
                                        background: transparent !important;
                                    }
                                    .selected {
                                        position: relative;
                                        outline: 2px solid #5b8dee !important;
                                        outline-offset: 1px;
                                        background: rgba(91, 141, 238, 0.05);
                                        border-radius: 2px;
                                        transition: all 0.2s ease;
                                    }
                                    /* Hover state for editable containers */
                                    [cy-xpath]:hover {
                                        outline: 1px dashed #5b8dee;
                                        outline-offset: 1px;
                                    }
                                    .gu-over {
                                        border: 2px dashed #007bff;
                                        background-color: #e9f5ff;
                                    }
                                    /* Premium Dynamic Field Styling */
                                    [cy-type='dynamic'] {
                                        background-color: #e7f3ff !important;
                                        color: #0056b3 !important;
                                        border: 1px solid #b3d7ff !important;
                                        padding: 2px 4px !important;
                                        border-radius: 4px !important;
                                        font-family: inherit;
                                        display: inline-block;
                                        max-width: 100%;
                                        overflow: hidden;
                                        text-overflow: ellipsis;
                                        vertical-align: middle;
                                        font-weight: 500;
                                        cursor: pointer;
                                    }
                                    [cy-type='dynamic']:hover {
                                        background-color: #d1e9ff !important;
                                        border-color: #80bdff !important;
                                        box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.1);
                                    }
                                    /* Special label for empty fields to show path */
                                    [cy-type='dynamic'][t-field]:empty::before,
                                    [cy-type='dynamic'][t-out]:empty::before,
                                    [cy-type='dynamic'][t-esc]:empty::before {
                                        content: "{" attr(t-field) attr(t-out) attr(t-esc) "}";
                                        font-size: 0.85em;
                                        opacity: 0.7;
                                        font-style: italic;
                                    }

                                    .branch-option {
                                        padding: 12px;
                                        margin: 8px 0;
                                        background: #f8f9fa;
                                        border: 2px solid #dee2e6;
                                        border-radius: 5px;
                                        cursor: pointer;
                                        transition: all 0.2s;
                                    }
                                    .branch-option:hover {
                                        border-color: #3b82f6;
                                        background: #e7f3ff;
                                    }
                                    .branch-option.active {
                                        background: #3b82f6;
                                        color: white;
                                        border-color: #3b82f6;
                                    }
                                    .branch-type {
                                        font-weight: bold;
                                        font-family: monospace;
                                        display: block;
                                        margin-bottom: 5px;
                                    }
                                    .branch-condition {
                                        font-size: 11px;
                                        color: #666;
                                        font-family: monospace;
                                        word-break: break-all;
                                    }
                                    .branch-option.active .branch-condition {
                                        color: #e3e3e3;
                                    }
                                    .col-insert-btn {
                                        border: none;
                                        background: none;
                                        color: #05306d;
                                        cursor: pointer;
                                        padding: 0 3px;
                                        font-size: 18px;
                                        position: relative;
                                    }

                                    .col-insert-btn::after {
                                        content: "";
                                        position: absolute;
                                        left: 50%;
                                        bottom: -15px;
                                        transform: translateX(-50%);
                                        width: 2px;
                                        height: 20px;
                                        background: #611e13;
                                    }
                                </style></data>"""
        head_content = etree.fromstring(head_content.encode())
        for child in head_content:
            head_el.append(child)

        # ── Preserve <t> QWeb tags through the HTML parse ──────────────────────
        # lxml's HTML parser does not know about <t> and silently strips the tags
        # (while keeping their children), which destroys t-foreach/t-set wrappers.
        # We temporarily rename <t ...> → <cy-qweb-t ...> and restore afterward.
        html_body_safe = re.sub(r'<t(\s|>|/)', r'<cy-qweb-t\1', html_body)
        html_body_safe = html_body_safe.replace('</t>', '</cy-qweb-t>')

        custom_doc = html.fromstring(html_body_safe)
        annotated_custom_doc = self.annotate_template(custom_doc)
        main_el = container_doc.xpath('//div[@id="wrapwrap"]/main')[0]
        for child in annotated_custom_doc:
            main_el.append(child)

        # footer_el = custom_doc.xpath('//t[@t-name="web.external_layout_standard"]//div[contains(@t-attf-class, "o_standard_footer")]')
        # print('footer_el',footer_el)
        # footer_el = footer_el[0] if footer_el else None
        # if footer_el is not None and footer_el.getparent() is not None:
        #     footer_el.getparent().remove(footer_el)
        #     main_el.append(footer_el)
        final_html = etree.tostring(container_doc, encoding='unicode', method='html')
        # print('final_html', final_html)

        # ── Restore <cy-qweb-t ...> back to real <t ...> ─────────────────────
        final_html = re.sub(r'<cy-qweb-t(\s|>|/)', r'<t\1', final_html)
        final_html = final_html.replace('</cy-qweb-t>', '</t>')

        return final_html

    # --------------------------------------------------------------
    # Recursive node annotation
    # --------------------------------------------------------------
    def annotate_template(self, custom_doc):
        """
        Annotate each element in the given XML (lxml element or tree) with:
          - cy-type: 'dynamic' if element has any t-* attribute else 'static'
        (cy-xpath and cy-template are now added BEFORE expansion)
        """
        root = custom_doc.getroot() if isinstance(custom_doc, etree._ElementTree) else custom_doc

        def annotate(node):
            if not isinstance(node.tag, str) or node.tag in ["p", "b", "i", "u", "em", "strike",
                                                             "sub", "sup", "blockquote",
                                                             "h1", "h3", "br", "strong", "thead", "tbody",
                                                             "cy-qweb-t"]:
                # Skip cy-qweb-t (renamed <t> nodes) — these are pure QWeb control-flow nodes
                # and must not receive cy-type so the JS editor ignores them as containers.
                return

            # --- Determine type ---
            cy_type = "dynamic" if any(
                k in ["t-out", "t-esc", "t-field"] for k in node.attrib.keys()) else "static"
            node.set("cy-type", cy_type)

            for child in node:
                annotate(child)

        annotate(root)
        return custom_doc

    # --------------------------------------------------------------
    # Recursive internal helper
    # --------------------------------------------------------------
    def _expand_template_for_iframe(self, template_name, depth, max_depth, cache):
        """Recursively expand inner t-calls while skipping web/report templates."""
        if depth > max_depth:
            return f"<!-- recursion limit reached for {template_name} -->"

        if template_name in cache:
            return cache[template_name]

        view = self.env.ref(template_name)
        if not view:
            return f"<!-- missing template: {template_name} -->"

        arch = view._get_combined_arch()  # raw template XML, no merged web layouts
        try:
            root = arch
        except Exception:
            raise ValidationError("Architecture missing")
        tree = etree.ElementTree(root)
        for node in root.iter():
            if isinstance(node.tag, str) and node.tag not in ["p", "b", "i", "u", "em", "strike", "sub", "sup", "blockquote", "h1", "h3", "br", "strong", "thead", "tbody"]:
                # <t> nodes (t-foreach, t-set, t-if etc.) MUST get cy-xpath
                # so they are preserved in the inheritance XML.
                if not (node.tag in ["span"] or 'c_new' in (node.attrib.get('class', '').split())):
                    if 'cy-xpath' not in node.attrib:
                        node.set("cy-xpath", tree.getpath(node))
                    if 'cy-template' not in node.attrib:
                        node.set("cy-template", template_name)

        # Find all <t t-call="..."> nodes
        for node in list(root.xpath(".//t[@t-call]")):
            called_name = node.get("t-call")
            # Skip global layout or report wrappers
            if not called_name or called_name in ["web.html_container",
                                                  "{{company.external_report_layout_id.sudo().key}}"]:
                continue

            expanded = self._expand_template_for_iframe(
                called_name, depth + 1, max_depth, cache
            )

            # Parse called template
            try:
                sub_root = etree.fromstring(f"<root>{expanded}</root>".encode("utf-8"))
            except Exception:
                continue

            # Insert children before existing ones
            for ch in reversed(list(sub_root)):
                node.insert(0, copy.deepcopy(ch))

            node.insert(0, etree.Comment(f"expanded from {called_name}"))

        xml_string = etree.tostring(root, encoding="unicode", pretty_print=True)
        cache[template_name] = xml_string
        return xml_string

    # @api.model
    # def get_iframe_rendered_template(self, template_name, max_depth=8):
    #     """
    #     Render a full template for iframe editing:
    #     - Expands internal t-calls.
    #     - Applies inherited views manually to track sources.
    #     - Preserves <t> nodes (does not solve t directives).
    #     - Returns HTML string ready to embed in <iframe srcdoc>.
    #     """
    #     cache = {}
    #
    #     # Get expanded template with source tracking
    #     root_element = self._expand_template_for_iframe(
    #         template_name, depth=0, max_depth=max_depth, cache=cache
    #     )
    #
    #     html_container = self.env['ir.qweb']._render('web.html_container', {})
    #     container_doc = html.fromstring(html_container)
    #
    #     # adding mediumeditor to head
    #     head_el = container_doc.xpath('//head')[0]
    #     head_content = """<data><style>
    #                                 .snippet {
    #                                     padding: 8px;
    #                                     margin: 4px;
    #                                     border: 1px solid #888;
    #                                     border-radius: 10px;
    #                                     background: #f8f8f8;
    #                                     cursor: grab;
    #                                 }
    #                                 .medium-editor-element::selection {
    #                                     background: transparent !important;
    #                                 }
    #                                 .selected {
    #                                     position: relative;
    #                                     outline: 2px dashed #4a90e2;
    #                                     outline-offset: 2px;
    #                                     background: repeating-linear-gradient(
    #                                         45deg,
    #                                         rgba(74, 144, 226, 0.15),
    #                                         rgba(74, 144, 226, 0.15) 10px,
    #                                         rgba(74, 144, 226, 0.05) 10px,
    #                                         rgba(74, 144, 226, 0.05) 20px
    #                                     );
    #                                     animation: borderStripe 3s linear infinite;
    #                                     border-radius: 4px;
    #                                     transition: box-shadow 0.2s ease, transform 0.2s ease;
    #                                 }
    #                                 .gu-over {
    #                                     border: 2px dashed #007bff;
    #                                     background-color: #e9f5ff;
    #                                 }
    #                                 [cy-type='dynamic'] {
    #                                     background-color: #D1D1D1;
    #                                     user-select: all;
    #                                     -webkit-user-select: all;
    #                                     -moz-user-select: all;
    #                                 }
    #                                 .branch-option {
    #                                     padding: 12px;
    #                                     margin: 8px 0;
    #                                     background: #f8f9fa;
    #                                     border: 2px solid #dee2e6;
    #                                     border-radius: 5px;
    #                                     cursor: pointer;
    #                                     transition: all 0.2s;
    #                                 }
    #                                 .branch-option:hover {
    #                                     border-color: #3b82f6;
    #                                     background: #e7f3ff;
    #                                 }
    #                                 .branch-option.active {
    #                                     background: #3b82f6;
    #                                     color: white;
    #                                     border-color: #3b82f6;
    #                                 }
    #                                 .branch-type {
    #                                     font-weight: bold;
    #                                     font-family: monospace;
    #                                     display: block;
    #                                     margin-bottom: 5px;
    #                                 }
    #                                 .branch-condition {
    #                                     font-size: 11px;
    #                                     color: #666;
    #                                     font-family: monospace;
    #                                     word-break: break-all;
    #                                 }
    #                                 .branch-option.active .branch-condition {
    #                                     color: #e3e3e3;
    #                                 }
    #                                 .col-insert-btn {
    #                                   border: none;
    #                                   background: none;
    #                                   color: #05306d;
    #                                   cursor: pointer;
    #                                   padding: 0 3px;
    #                                   font-size: 18px;
    #                                   position: relative;
    #                                 }
    #
    #                                 .col-insert-btn::after {
    #                                   content: "";
    #                                   position: absolute;
    #                                   left: 50%;
    #                                   bottom: -15px;
    #                                   transform: translateX(-50%);
    #                                   width: 2px;
    #                                   height: 20px;
    #                                   background: #611e13;
    #                                 }
    #                             </style></data>"""
    #     head_content = etree.fromstring(head_content.encode())
    #     for child in head_content:
    #         head_el.append(child)
    #
    #     # Annotate BEFORE converting to string (while we still have the element tree)
    #     annotated_root = self.annotate_template(root_element)
    #
    #     # Convert to string and parse as HTML
    #     xml_string = etree.tostring(annotated_root, encoding='unicode', method='html')
    #     custom_doc = html.fromstring(xml_string)
    #
    #     main_el = container_doc.xpath('//div[@id="wrapwrap"]/main')[0]
    #     for child in custom_doc:
    #         main_el.append(child)
    #
    #     final_html = etree.tostring(container_doc, encoding='unicode', method='html')
    #     return final_html
    #
    # def annotate_template(self, root):
    #     """
    #     Annotate each element with:
    #       - cy-type: 'dynamic' if element has any t-* attribute else 'static'
    #       - cy-template: the source template name (already stored as data-source-template)
    #       - cy-xpath: XPath in the SOURCE template (already stored as data-source-xpath)
    #       - cy-source-view-id: database ID of the view to modify (already stored)
    #
    #     This just renames the temporary data-* attributes to cy-* attributes.
    #     """
    #     tree = etree.ElementTree(root)
    #
    #     def annotate(node):
    #         if not isinstance(node.tag, str) or node.tag in ["p", "b", "i", "u", "em", "strike",
    #                                                          "sub", "sup", "blockquote",
    #                                                          "h1", "h3", "br", "strong", "thead",
    #                                                          "tbody"]:
    #             return
    #
    #         # --- Determine type ---
    #         cy_type = "dynamic" if any(
    #             k in ["t-out", "t-esc", "t-field"] for k in node.attrib.keys()) else "static"
    #         node.set("cy-type", cy_type)
    #
    #         # Skip spans and special classes
    #         if node.tag in ["span"] or 'c_new' in (
    #                 node.attrib.get('class', '').split()):
    #             return
    #
    #         # --- Convert data-* attributes to cy-* attributes ---
    #         source_template = node.get('data-source-template')
    #         source_xpath = node.get('data-source-xpath')
    #         source_view_id = node.get('data-source-view-id')
    #
    #         if source_template:
    #             node.set("cy-template", source_template)
    #             del node.attrib['data-source-template']
    #
    #         if source_xpath:
    #             node.set("cy-xpath", source_xpath)
    #             del node.attrib['data-source-xpath']
    #
    #         if source_view_id:
    #             node.set("cy-source-view-id", source_view_id)
    #             del node.attrib['data-source-view-id']
    #
    #         for child in node:
    #             annotate(child)
    #
    #     annotate(root)
    #     return root
    #
    # def _expand_template_for_iframe(self, template_name, depth, max_depth, cache):
    #     """
    #     Recursively expand inner t-calls AND apply inherited views while tracking sources.
    #     Marks each node with data-source-* attributes for later annotation.
    #     """
    #     if depth > max_depth:
    #         comment = etree.Comment(f"recursion limit reached for {template_name}")
    #         return comment
    #
    #     if template_name in cache:
    #         return cache[template_name]
    #
    #     view = self.env.ref(template_name)
    #     if not view:
    #         comment = etree.Comment(f"missing template: {template_name}")
    #         return comment
    #
    #     # Start with base arch (NOT combined)
    #     base_arch = etree.fromstring(view.arch_db)
    #
    #     # Track all nodes from base view with data-* attributes
    #     base_tree = etree.ElementTree(base_arch)
    #     for node in base_arch.iter():
    #         if isinstance(node.tag, str):
    #             raw_xpath = base_tree.getpath(node)
    #             clean_xpath = self._clean_xpath(raw_xpath)
    #             node.set('data-source-view-id', str(view.id))
    #             node.set('data-source-template', template_name)
    #             node.set('data-source-xpath', clean_xpath)
    #
    #     # Apply all inherited views manually
    #     root = self._apply_inherited_views(base_arch, view)
    #
    #     # Now expand t-calls
    #     for node in list(root.xpath(".//t[@t-call]")):
    #         called_name = node.get("t-call")
    #
    #         if not called_name or called_name in ["web.html_container",
    #                                               "{{company.external_report_layout_id.sudo().key}}"]:
    #             continue
    #
    #         expanded = self._expand_template_for_iframe(
    #             called_name, depth + 1, max_depth, cache
    #         )
    #
    #         # Parse called template if it's a string
    #         if isinstance(expanded, str):
    #             try:
    #                 sub_root = etree.fromstring(f"<root>{expanded}</root>".encode("utf-8"))
    #             except Exception:
    #                 continue
    #         else:
    #             # It's already an element
    #             sub_root = etree.Element("root")
    #             sub_root.append(expanded)
    #
    #         # Insert children - data-* attributes are already on them
    #         for ch in reversed(list(sub_root)):
    #             new_child = copy.deepcopy(ch)
    #             node.insert(0, new_child)
    #
    #         node.insert(0, etree.Comment(f"expanded from {called_name}"))
    #
    #     cache[template_name] = root
    #     return root
    #
    # def _apply_inherited_views(self, base_arch, base_view):
    #     """
    #     Manually apply all inherited views.
    #     Marks new elements with data-source-* attributes.
    #     """
    #     root = base_arch
    #
    #     # Get all views that inherit from this one
    #     inherited_views = self.env['ir.ui.view'].search([
    #         ('inherit_id', '=', base_view.id),
    #         ('mode', '=', 'extension')  # Only extensions, not primary views
    #     ], order='priority,id')
    #
    #     for inherited_view in inherited_views:
    #         try:
    #             inherit_arch = etree.fromstring(inherited_view.arch_db)
    #         except Exception:
    #             continue
    #
    #         # Get inherited view's template name
    #         inherited_template_name = (inherited_view.key or
    #                                    inherited_view.xml_id or
    #                                    f"view_{inherited_view.id}")
    #
    #         # Process each xpath directive in the inherited view
    #         for xpath_node in inherit_arch.xpath(".//xpath"):
    #             expr = xpath_node.get("expr")
    #             position = xpath_node.get("position", "inside")
    #
    #             try:
    #                 # Find target nodes in the merged tree
    #                 targets = root.xpath(expr)
    #             except Exception:
    #                 continue
    #
    #             if not targets:
    #                 continue
    #
    #             target = targets[0]
    #
    #             # Apply inheritance based on position
    #             for child in xpath_node:
    #                 new_node = copy.deepcopy(child)
    #
    #                 # Track this node and all descendants
    #                 inherit_tree = etree.ElementTree(inherit_arch)
    #                 original_xpath = inherit_tree.getpath(child)
    #
    #                 self._mark_node_and_descendants(new_node,
    #                                                 inherited_view.id,
    #                                                 inherited_template_name,
    #                                                 original_xpath
    #                                                 )
    #
    #                 # Insert based on position
    #                 if position == "inside":
    #                     target.append(new_node)
    #                 elif position == "after":
    #                     parent = target.getparent()
    #                     if parent is not None:
    #                         index = list(parent).index(target)
    #                         parent.insert(index + 1, new_node)
    #                 elif position == "before":
    #                     parent = target.getparent()
    #                     if parent is not None:
    #                         index = list(parent).index(target)
    #                         parent.insert(index, new_node)
    #                 elif position == "replace":
    #                     parent = target.getparent()
    #                     if parent is not None:
    #                         index = list(parent).index(target)
    #                         parent.remove(target)
    #                         parent.insert(index, new_node)
    #                 elif position == "attributes":
    #                     # Update attributes on target
    #                     for attr_node in child:
    #                         if attr_node.tag == "attribute":
    #                             attr_name = attr_node.get("name")
    #                             target.set(attr_name, attr_node.text or "")
    #
    #     return root
    #
    # def _mark_node_and_descendants(self, node, view_id, template_name, xpath):
    #     """
    #     Mark a node and all its descendants with source tracking attributes.
    #     """
    #     if isinstance(node.tag, str):
    #         # Clean xpath: remove /data and /xpath tags
    #         clean_xpath = self._clean_xpath(xpath)
    #
    #         node.set('data-source-view-id', str(view_id))
    #         node.set('data-source-template', template_name)
    #         node.set('data-source-xpath', clean_xpath)
    #
    #     # Mark descendants (they share the same source)
    #     for child in node:
    #         if isinstance(child.tag, str):
    #             self._mark_node_and_descendants(child, view_id, template_name, xpath)
    #
    # def _clean_xpath(self, xpath):
    #     """
    #     Remove /data and /xpath segments from xpath string.
    #     Example: /data/xpath[2]/div[1]/span -> /div[1]/span
    #     """
    #     import re
    #     # Remove /data and /xpath with optional indices
    #     cleaned = re.sub(r'/data(?:\[\d+\])?', '', xpath)
    #     cleaned = re.sub(r'/xpath(?:\[\d+\])?', '', cleaned)
    #     # Ensure it starts with / if not empty
    #     if cleaned and not cleaned.startswith('/'):
    #         cleaned = '/' + cleaned
    #     return cleaned if cleaned else '/'