/** @odoo-module */
// Import necessary modules and components
import {registry} from "@web/core/registry";
import {Component, onWillStart, useRef, markup} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {useState} from "@odoo/owl";
import {jsonrpc} from "@web/core/network/rpc_service";
import {session} from "@web/session";
import { CompanyDetailsDialog } from "@cyllo_dashboard/js/company_dialog";


// Get the 'actions' category from the registry
const actionRegistry = registry.category("actions");

function htmlToText(html) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const result = [];

    function getText(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            result.push(node.textContent);
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.tagName === 'BR') {
                result.push('\n');
            }
            for (let childNode of node.childNodes) {
                getText(childNode);
            }
        }
    }
    getText(doc.body);
    return result.join('');
}

function textToHtml(text) {
    // Replace newline characters with <br> tags
    const htmlContent = text.replace(/\n/g, '<br>');
    return htmlContent;
}

// Define a new component named 'Cyllo Dashboard'
export class UserDashboard extends Component {
    setup() {
        super.setup(...arguments);
        this.orm = useService('orm');
        this.menuService = useService("menu");
        this.dialogService = useService("dialog");
        this.root = useRef("root")
        this.rootNonAdmin = useRef("root-non-admin")
        this.userID = session.uid
        this.session = session
        this.state = useState({
            shortcuts: {},
            loginUserDetails: {},
            userProfile: {},
            weatherDetails: {},
            activities: {},
            performanceInsights: {},
            cpuInsights: {},
            nonAdmin: {},
            notifType: false,
            autoEdit: false,
        })
        this.action = useService("action");
        this.getActivities();
        onWillStart(async () => {
            this.renderShortcuts();
            this.renderLoginUserDetails();
            this.renderNonAdminUserDetails();
            this.renderUserProfile();
            this.getIdleTime();
            this.renderWeatherNotification();
            this.renderPerformanceInsight();
            await this.orm.call('res.users', 'get_change_pwd_view_id').then((result) => {
                this.view_id = result;
            });
            await this.orm.call('res.users', 'get_groups').then((result) => {
                this.groups = result;
            });
            await this.orm.call('res.users', 'get_current_user_details').then((result) => {
                this.userId = result.id;
                this.tz = result.current_tz
            });

            await this.orm.call('res.users', 'get_auto_edit_value').then((result) => {
                this.state.autoEdit = result;
            });
        });
    }

    getIdleTime() {
        var now = new Date().getTime();
        jsonrpc('/get_idle_time/timer').then((data) => {
            if (data) {
                this.minutes = data
                this.idleTimer()
            }
        })
    }

    idleTimer() {
        var nowt = new Date().getTime();
        var date = new Date(nowt);
        date.setMinutes(date.getMinutes() + this.minutes);
        var updatedTimestamp = date.getTime();
        /** Running the count down using setInterval function */
        var idle = setInterval(() => {
            var now = new Date().getTime();
            var distance = updatedTimestamp - now;
            var days = Math.floor(distance / (1000 * 60 * 60 * 24));
            var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            var seconds = Math.floor((distance % (1000 * 60)) / 1000);
            $("#idle_timer").empty();
            if (hours && days) {
                $("#idle_timer").append('<span>' + days + "d " + hours + "h " + minutes + "m " + seconds + "s " + '</span>');
            } else if (hours) {
                $("#idle_timer").append('<span>' + hours + "h " + minutes + "m " + seconds + "s " + '</span>');
            } else {
                $("#idle_timer").append('<span>' + minutes + "m " + seconds + "s " + '</span>')
            }
            /** if the countdown is zero the link is redirect to the login page*/
            if (distance < 0) {
                clearInterval(idle);
                $("#idle_timer").empty();
                $("#idle_timer").append("EXPIRED");
                location.replace("/web/session/logout")
            }
        }, 1000);
        /**
         checking if the onmouse-move event is occur
         */
        document.onmousemove = () => {
            var nowt = new Date().getTime();
            var date = new Date(nowt);
            date.setMinutes(date.getMinutes() + this.minutes);
            updatedTimestamp = date.getTime();
        };
        /**
         checking if the onkeypress event is occur
         */
        document.onkeypress = () => {
            var nowt = new Date().getTime();
            var date = new Date(nowt);
            date.setMinutes(date.getMinutes() + this.minutes);
            updatedTimestamp = date.getTime();
        };
        /**
         checking if the onclick event is occur
         */
        document.onclick = () => {
            var nowt = new Date().getTime();
            var date = new Date(nowt);
            date.setMinutes(date.getMinutes() + this.minutes);
            updatedTimestamp = date.getTime();
        };
        /**
         checking if the ontouchstart event is occur
         */
        document.ontouchstart = () => {
            var nowt = new Date().getTime();
            var date = new Date(nowt);
            date.setMinutes(date.getMinutes() + this.minutes);
            updatedTimestamp = date.getTime();
        }
        /**
         checking if the onmousedown event is occur
         */
        document.onmousedown = () => {
            var nowt = new Date().getTime();
            var date = new Date(nowt);
            date.setMinutes(date.getMinutes() + this.minutes);
            updatedTimestamp = date.getTime();
        }
        /**
         checking if the onload event is occur
         */
        document.onload = () => {
            var nowt = new Date().getTime();
            var date = new Date(nowt);
            date.setMinutes(date.getMinutes() + this.minutes);
            updatedTimestamp = date.getTime();
        }
    }

    renderWeatherNotification() {
        jsonrpc('/weather/notification/check').then((data) => {
            if (data['cod'] == 200) {
                var temp = Math.floor(data.main.temp - 273);
                this.state.weatherDetails.city = data.name
                this.state.weatherDetails.temp = temp
                this.state.weatherDetails.description = data.weather[0].description
                this.state.weatherDetails.weather = data.weather[0].main
                this.state.weatherDetails.icon = data.weather[0].icon
            }
        })
    }

    editSignature() {
        this.rootNonAdmin.el.querySelector('#signatureContent').style.display = 'none'
        this.rootNonAdmin.el.querySelector('#email-sign-textarea').classList.remove("d-none");
        this.rootNonAdmin.el.querySelector('#signatureSaveBtn').classList.remove("d-none");
        this.rootNonAdmin.el.querySelector('#signatureEditBtn').style.display = 'none';
    }

    saveSignature(){
        var textarea = this.rootNonAdmin.el.querySelector('#email-sign-textarea')
        var textContent = textarea.value;
        var htmlContent = textToHtml(textContent);
        this.orm.write("res.users", [this.userId], {'signature': htmlContent});
        this.env.services['action'].doAction('reload_context');
    }

    async onClickPermissions() {
         this.env.services['action'].doAction({
             name: "Permissions",
             type: 'ir.actions.act_window',
             res_model: 'res.groups',
             views: [[false, 'tree'], [false, 'form']],
             domain: [['id', 'in', this.groups]],
             target: 'current',
         });
    }

    async renderNonAdminUserDetails(){
        if(!session.is_admin) {
           const user = await this.orm.call('res.users', 'get_non_admin_user_details' ,[session.user_id[0]])
           this.state.nonAdmin = user
        }
    }

    get markupSignature() {
        return markup(this.state.nonAdmin.signature);
    }

    get signature() {
        return htmlToText(this.state.nonAdmin.signature);
    }


    async onClickGroups() {
        const user = await this.orm.call('res.users', 'get_non_admin_user_details' ,[session.user_id[0]])
        this.env.services['action'].doAction({
            name: 'Groups',
            type: 'ir.actions.act_window',
            res_model: 'res.groups',
            views: [[false, 'tree'], [false, 'form']],
            target: 'current',
            context: {'create': false, 'delete': false},
            domain: [['id','in', user.groups_id]],
        });
    }

    async onClickAccessRights() {
        const user = await this.orm.call('res.users', 'get_non_admin_user_details' ,[session.user_id[0]])
        this.env.services['action'].doAction({
            name: 'Access Rights',
            type: 'ir.actions.act_window',
            res_model: 'ir.model.access',
            views: [[false, 'tree']],
            target: 'current',
            context: {'create': false, 'delete': false},
            domain: [['id','in', user.model_access]],
        });
    }

    async onClickRecordRules() {
        const user = await this.orm.call('res.users', 'get_non_admin_user_details' ,[session.user_id[0]])
        this.env.services['action'].doAction({
            name: 'Record Rules',
            type: 'ir.actions.act_window',
            res_model: 'ir.rule',
            views: [[false, 'tree']],
            target: 'current',
            context: {'create': false, 'delete': false},
            domain: [['id','in', user.rule_groups]],
        });
    }

    onClickCompany(company) {
        this.dialogService.add(CompanyDetailsDialog, {
            company: company,
            model: "res.company",
            title: company.name,
        })
    }

    onClickChangePassword() {
        this.env.services['action'].doAction({
            name: "Change Password",
            type: 'ir.actions.act_window',
            res_model: 'change.password.own',
            views: [[this.view_id, 'form']],
            target: 'new',
        });
    }

    renderUserProfile() {
        this.orm.call('res.users', 'get_current_user_details').then((result) => {
            this.state.userProfile = result;
            this.userId = result.id;
        });
    }

    async renderShortcuts() {
        try {
            const menuList = [];
            const menuItems = await this.orm.searchRead('shortcut.menu', [['create_uid', '=', session.uid]]);
            this.state.shortcuts = menuItems
        } catch (error) {
            console.error('Error fetching shortcuts:', error);
        }
    }

    isCompleteNameUnique(name) {
        const count = this.state.shortcuts.filter(shortcut => shortcut.name === name).length;
        return count === 1;
    }

    onChangeLang(ev) {
        this.orm.write("res.users", [this.userId], {'lang': ev.target.value});
        this.env.services['action'].doAction('reload_context');
    }

    onChangeTimezone(ev) {
        this.orm.write("res.users", [this.userId], {'tz': ev.target.value});
        this.env.services['action'].doAction('reload_context');
    }

    onClickShortCutMenu(data) {
    try {
        let menu = this.menuService.getMenuAsTree(data.menu_id[0]);
        this.menuService.selectMenu(menu);
    } catch (error) {
        console.error('Error:', error);
        // If getMenuAsTree returns undefined, execute the fallback code
        this.env.services['action'].doAction({
            name: data.display_name,
            type: 'ir.actions.act_window',
            res_model: data.model,
            views: [[false, 'tree']],
            target: 'current',
        });
    }
}

    onToggleAutoEdit(ev) {
        this.state.autoEdit = ev.target.checked
        this.orm.write("res.users", [this.userId], {'auto_edit': ev.target.checked});
        this.env.services['action'].doAction('reload_context');
    }

    onToggleAutoEditNonAdmin(ev){
        this.state.autoEdit = ev.target.checked
        this.orm.call("res.users", 'toggle_auto_edit', [ev.target.checked]);
        this.env.services['action'].doAction('reload_context');
    }

    onClickShortCutAdd(model) {
        if (model){
            this.env.services['action'].doAction({
                type: 'ir.actions.act_window', res_model: model, views: [[false, 'form']], target: 'new',
            });
        }
    }

    renderLoginUserDetails() {
        var order = 'desc';
        this.orm.call('login.user.detail', 'search_read', [], {
            order: 'id desc', limit: 5,
        }).then((result) => {
            this.state.loginUserDetails = result;
        });
    }

    async getActivities() {
        const groups = await this.env.services.orm.call("res.users", "systray_get_activities");
        let total = 0;
        for (const group of groups) {
            total += group.total_count || 0;
        }
        this.state.activities = groups;
    }

    openActivityGroup(group, filter = "all") {
        document.body.click();
        const context = {
            force_search_count: 1,
        };
        if (filter === "all") {
            context.search_default_activities_overdue = 1;
            context.search_default_activities_today = 1;
        } else {
            context["search_default_activities_" + filter] = 1;
        }
        var domain = [["activity_ids.user_id", "=", this.userId]];
        if (group.model === 'mail.activity') {
            domain = [["user_id", "=", this.userId]];
        }
        const views = this.availableViews(group);
        this.action.doAction({
            context,
            domain,
            name: group.name,
            res_model: group.model,
            search_view_id: [false],
            type: "ir.actions.act_window",
            views,
        }, {
            clearBreadcrumbs: true,
            viewType: group.view_type,
        });
    }

    onClickAction(action, group) {
        document.body.click(); // hack to close dropdown
        if (action.action_xmlid) {
            this.env.services.action.doAction(action.action_xmlid);
        } else {
            let domain = [["activity_ids.user_id", "=", this.userId]];
            if (group.domain) {
                domain = domain.concat(group.domain);
            }
            this.env.services['action'].doAction({
                domain,
                name: group.name,
                res_model: group.model,
                type: "ir.actions.act_window",
                views: this.availableViews(group),
            }, {clearBreadcrumbs: true, viewType: "activity"});
        }
    }

    availableViews(group) {
        return [[false, "kanban"], [false, "list"], [false, "form"], [false, "activity"],];
    }

    onInputNotifType(ev){
        this.orm.write("res.users", [this.userId], {'notification_type': ev.target.value});
        this.env.services['action'].doAction('reload_context');
    }
    onChangeOdooBotStatus(ev){
        this.orm.write("res.users", [this.userId], {'odoobot_state': ev.target.value});
    }

    renderPerformanceInsight() {
        Promise.all([jsonrpc('/performance'), jsonrpc('/cpu', {})]).then(([performanceResult, cpuData]) => {
            const {
                progressbar,
                cpu: cpu_performance,
                ram_percent,
                rom_in_gb: ram_gb,
                total_ram,
                ram_in_gb: used_ram_gb,
                available_ram,
                used_memory,
                free_memory,
                core_usage_formatted_list,
                cpu_chart_values,
                total_memory,
                total_cpu_usage,
                used_memory_history,
                used_ram_history,
                hardware_temperature_history,
                cpu_usage_history,
                is_admin
            } = performanceResult;
            this.state.performanceInsights = performanceResult;
            this.state.cpuInsights = cpuData;
        });
    }
}
UserDashboard.template = "UserDashboard";
actionRegistry.add('cyllo_user_dashboard', UserDashboard);
