/** @odoo-module **/
import { registry } from "@web/core/registry";
import { CharField, charField } from '@web/views/fields/char/char_field';
import { _t } from "@web/core/l10n/translation";
import { useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
export class FileToPath extends CharField {
   setup(){
       super.setup();
       this.input = useRef('video_file')
        this.orm = useService("orm");
        this.actionService = useService("action");
   }
   async _onSelectFile(ev){
   try {
        const message = _t("Uploading Video...");
        this.env.services.ui.block(message);
        var self =this
        var datas=ev.target.files[0]
        const credential = await this.orm.call("social.media.post", "get_youtube_account", [[this.props.record.evalContext.context.default_youtube_post_id]]);
        const response = await fetch('https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status,contentDetails', {
        method: 'POST',
        headers: {
        'Authorization': `Bearer ${credential['key']}`,
        'Content-Type': 'application/json; charset=UTF-8',
        'X-Upload-Content-Length': datas.size,
        'X-Upload-Content-Type': datas.type
        },
        body: JSON.stringify({
        status: {privacyStatus: "private"},
        snippet: {
        title: credential['details']['name'],
        description: credential['details']['video_description'],
        }
        })
        });
        if(response.headers.get('Location')){
        const location=response.headers.get('Location')
        const UploadResponse = await fetch(location, {
        method: 'PUT',
        headers: {
        'Authorization': `Bearer ${credential['key']}`,
        'Content-Length': datas.size,
        'Content-Type': datas.type
        },
        body: datas
        });
        UploadResponse.json().then(async data => {
            var video_id=data.id
            await self.orm.write("social.media.post", [self.props.record.evalContext.context.default_youtube_post_id], { youtube_video_number: video_id,state:"queue" });
        });
        }
        else{
        self.actionService.doAction({
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
        'message': "Exceeded Daily Upload Limit,Check Account",
        'type': 'warning',
                 }
        })
        }
        self.env.services.ui.unblock();
        }
   catch (e) {
        self.actionService.doAction({
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
        'message': "Exceeded Daily Upload Limit,Check Account",
        'type': 'warning',
                 }
        })
              }
}
}
FileToPath.template = 'cyllo_youtube.FileToPathConvertor';

export const FileToPathField = {
    ...charField,
    component: FileToPath,
};
registry.category("fields").add("file_to_path", FileToPathField);
