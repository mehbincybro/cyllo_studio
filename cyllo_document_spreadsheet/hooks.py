# -*- coding: utf-8 -*-
def uninstall_hook(env):
    """
    Removes the xlsx file from document.file
    :param env:
    :return:
    """
    for document in env['document.file'].search([]):
        if document.extension == "xlsx":
            document.unlink()
