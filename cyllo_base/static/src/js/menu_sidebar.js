/** @odoo-module **/
const {useState, Component, xml, useEffect, useRef, onMounted, onWillStart} = owl;
import {session} from "@web/session";
import {jsonrpc} from "@web/core/network/rpc_service";
import {useBus, useService} from "@web/core/utils/hooks";
import {ActionContainer} from '@web/webclient/actions/action_container';
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {_t} from "@web/core/l10n/translation";
import {sprintf} from "@web/core/utils/strings";
import {registry} from "@web/core/registry";
import {clearUncommittedChanges} from "@web/webclient/actions/action_service";


export class MenuSideBar extends Component {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.action = useService("action");
        this.rpc = useService("rpc");
        this.websiteService = this.env.services.website
        this.session = session;
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.resetOptions = {
            condition: false,
            actionId: 0,
        }
        this.menuService = useService("menu");
        this.env.bus.addEventListener("RESET_MENUS", async (event) => {
            const {mainMenu} = event.detail;
            this.resetOptions.actionId++
            this.resetOptions.condition = mainMenu || false;
            this.state.isApp = true
            if (this.resetOptions.condition) {
                await this.menuService.reload()
                this.state.menus = this.getMenus()
                this.resetOptions.condition = false;
            }
        })
        let isSidebarOn = localStorage.getItem('isSidebarOn');
        this.isSidebarOnBoolean = (isSidebarOn === null || isSidebarOn === 'true');
        this.state = useState({
            pinnedMenu: session.pinned_menu,
            isSidebarOn: this.isSidebarOnBoolean,
            isApp: !parseInt(localStorage.getItem('cy_selected_app')),
            currentSelectedApp: parseInt(localStorage.getItem('cy_selected_app')) || false,
            currentSelectedMenu: parseInt(localStorage.getItem('cy_selected_menu')) || false,
            menus: [],
            apps: this.menuService.getApps(),
            isAddedToShortcut: session.is_added_to_shortcut_menu,
            selectedAppName: localStorage.getItem('selectedAppName'),
            isCollapseOn: false,
            isHomeActive: true,
        })
        this.cyLeftSidebar = useRef('cy-left-sidebar')
        useBus(this.env.bus, 'onclickMenuBar', (v) => this.OnclickMenuBar(v));
        useBus(this.env.bus, 'GLOBAL-SEARCH-CLICKED', () => this.onClickLogo())
        useBus(this.env.bus, 'OPEN-MENU', (ev) => this.openMenu(ev.detail))

        useEffect(() => {
            const getMenu = async () => {
                this.state.menus = this.getMenus()
                if (this.resetOptions.condition) {
                    await this.menuService.reload()
                    this.state.menus = this.getMenus()
                    this.resetOptions.condition = false;
                }
            }
            getMenu()
        }, () => [this.state.isApp, this.resetOptions.actionId])

        onMounted(async () => {
            this.mainMenuVisibility = (localStorage.getItem('mainMenuVisibility') !== null) ? (localStorage.getItem('mainMenuVisibility') === 'true') : true;
            if (!this.isSidebarOnBoolean) {
                this.cyLeftSidebar.el.parentElement.classList.add('menuListFixed')
            }
        });

        onWillStart(async () => {
            const {
                id: homeActionId,
                active
            } = await this.orm.call('ir.ui.menu', 'get_action_home_id', []);
            this.homeActionId = homeActionId;
            this.state.isHomeActive = active;
            this.state.isAddedToShortcut = await this.orm.searchRead('shortcut.menu', []);
        });
        this.busService = this.env.services.bus_service
        this.channel = "reset_menu"
        this.busService.addChannel(this.channel)
        this.busService.addEventListener("notification", this.onResetMenu.bind(this))
    }

    openMenu(menu) {
        if (this.state.currentSelectedApp !== menu.appID) {
            this.onClickMenu(menu.appID, true)
        }
        if (menu.appID !== menu.id){
            this.onClickMenu(menu.id, false)
        }
    }

    async getSvg(svgPath, appId) {
        const iconSvgPath = `${svgPath.split(',')[0]}/${svgPath.split(',')[1]}`;
        try {
            const response = await fetch(iconSvgPath);
            const data = await response.text();
            const svgContainer = this.cyLeftSidebar.el?.querySelector(`#svg-container-${appId}`);
            if (svgContainer && response.status === 200) {
                svgContainer.innerHTML = data;
            }
            this.cyLeftSidebar.el?.querySelectorAll(
                ".cy-left-sidebar .cy-svg-container *[style*='#26261A'], .cy-left-sidebar .cy-svg-container [fill='#26261A']"
            ).forEach(rect => {
                rect.setAttribute('style', 'fill: transparent !important;')
            });
        } catch (error) {
            console.error('Error fetching SVG:', error);
        }
    }

    onKeyupSearch(ev) {
        const filter = this.cyLeftSidebar.el.querySelector('input').value.toLowerCase();
        this.cyLeftSidebar.el.querySelectorAll("li").forEach(menu => {
            const link = menu.querySelector("a");
            if (link) {
                const text = (link.textContent || link.innerText).toLowerCase();
                menu.style.display = text.includes(filter) ? "" : "none";
            }
        });
    }

    async onResetMenu({
        detail: notifications
    }) {
        notifications = notifications.filter(item => item.payload.channel === this.channel)
        notifications.forEach(item => {
            localStorage.setItem("isSidebarOn", true)
            localStorage.setItem("cy_selected_app", 0 || false)
        })
    }

    collapseMenu(v) {
        this.state.isCollapseOn = [null, undefined].includes(v.detail) ? !this.state.isCollapseOn : v.detail.isCollapse

        if (this.state.isCollapseOn) {
            this.cyLeftSidebar.el.parentElement.classList.add('cy_menu-collapsed');
        } else {
            this.cyLeftSidebar.el.parentElement.classList.remove('cy_menu-collapsed');
        }
        this.env.bus.trigger("SIDEBAR_MENU_TOGGLE", {
            isSidebarOn: !this.state.isCollapseOn
        })
    }

    onClickMenuIcon() {
        this.mainMenuVisibility = !this.mainMenuVisibility
        this.state.isSidebarOn = !this.state.isSidebarOn;
        this.cyLeftSidebar.el.parentElement.classList.add('menuListFixed')
        localStorage.setItem("isSidebarOn", this.state.isSidebarOn)
        localStorage.setItem('mainMenuVisibility', this.mainMenuVisibility)
        this.env.bus.trigger("SIDEBAR_MENU_TOGGLE", {
            isSidebarOn: this.mainMenuVisibility
        })
    }

    onClickLogo() {
        this.env.bus.trigger('RESET_MENUS', {
            condition: false
        })
        this.state.isSidebarOn = true
        this.cyLeftSidebar.el.parentElement.classList.remove('menuListFixed')
        this.cyLeftSidebar.el.querySelectorAll('.cy_active_main_menu').forEach(menu => menu.classList.remove('cy_active_main_menu'));
        this.state.currentSelectedApp = false
        localStorage.setItem('isSidebarOn', true)
        localStorage.setItem("cy_selected_app", false)
        localStorage.setItem("cy_selected_menu", 0 || false)
        this.state.isCollapseOn = false
        this.cyLeftSidebar.el.parentElement.classList.remove('cy_menu-collapsed');
        this.env.bus.trigger("homeButtonClicked", {
            isSubMenuOn: true
        })
    }

    async onClickHome() {
        this.onClickMenu(this.homeActionId, true)
        this.env.bus.trigger('CLEAR-MENU', {
            fromClose: true
        });
    }

    resetSelectMenu(menuId) {
        sessionStorage.removeItem("X2manyList")
        this.cyLeftSidebar.el.querySelectorAll('.cy_active_menu').forEach(menu => menu?.classList.remove('cy_active_menu'));
        const menu = `#main_menu${menuId}`;
        this.cyLeftSidebar.el.querySelector(menu)?.classList.add('cy_active_menu');
        localStorage.setItem("cy_selected_menu", 0 || false)
    }

    openContextMenu() {
        event.preventDefault();
        var activeContextMenu = this.cyLeftSidebar.el.querySelectorAll('.context-menu[style="display: block;"]')
        activeContextMenu.forEach((menu) => {
            menu.style.display = 'none'
        })
        var cyLeftSidebarContextMenu = event.target.querySelector('.context-menu')
        if (cyLeftSidebarContextMenu) {
            cyLeftSidebarContextMenu.style.display = 'block';
            document.addEventListener('click', function() {
                cyLeftSidebarContextMenu.style.display = 'none';
            });
        }
    }

    OnclickMenuBar(v) {
        this.collapseMenu(v)
    }

    getMenuIdFromUrl() {
        const hash = window.location.hash; // e.g. "#action=164&active_id=1&model=hr.employee&view_type=list&cids=1&menu_id=117"
        const params = new URLSearchParams(hash.slice(1)); // Remove "#" and parse
        return params.get('menu_id');
    }

    async AddToShortcuts(menuObj) {
        try {
            var {
                actionID,
                name,
                actionModel
            } = menuObj
            if (actionID) {
                const result = await jsonrpc('/menubar/add_to_shortcuts', {
                    actionId: actionID,
                    name: name,
                    actionModel: actionModel,
                    model: this.env?.searchModel?.resModel || false,
                    menu_id: parseInt(this.action?.currentController?.action?.context?.params?.menu_id || this.getMenuIdFromUrl()),
                });
                if (result) {
                    this.state.isAddedToShortcut.push({
                        actionID,
                        name
                    })
                    this.notification.add(sprintf(_t(`"%s" added to your shortcuts`), name), {
                        title: 'Shortcut Added',
                        type: "success",
                    });
                    this.env.services['action'].doAction('reload_context');
                } else {
                    this.notification.add(_t("Could not add shortcut to dashboard"), {
                        type: "danger",
                    });
                }
            }
        }
        catch (e) {
            console.error(e);
            this.notification.add(_t("Could not add shortcut to dashboard"), {
                type: "danger",
            });
        }
        var activeContextMenu = this.cyLeftSidebar.el.querySelectorAll('.context-menu[style="display: block;"]')
        activeContextMenu.forEach((menu) => {
            menu.style.display = 'none'
        })
    }

    async RemoveFromShortcut(menuObj) {
        var {actionID, name, actionModel} = menuObj
        if (actionID) {
            const result = await jsonrpc('/menubar/remove_from_shortcuts', {
                actionId: actionID,
                name: name,
                model: this.env?.searchModel?.resModel || false,
                actionModel: actionModel
            });
            if (result) {
                this.state.isAddedToShortcut = this.state.isAddedToShortcut.filter(item => item.id !== menuObj.id)
                this.notification.add(sprintf(_t(`"%s" removed from shortcut`), name), {
                    title: 'Shortcut Removed',
                    type: "warning",
                });
                this.env.services['action'].doAction('reload_context');
            }
        }
        var activeContextMenu = this.cyLeftSidebar.el.querySelectorAll('.context-menu[style="display: block;"]')
        activeContextMenu.forEach((menu) => {
            menu.style.display = 'none'
        })
    }

    OnMouseEnterSidebar() {
        this.state.isSidebarOn = true;
    }

    OnMouseLeaveSidebar() {
        this.state.isSidebarOn = false;
    }

    get(xmlId) {
        return registry.category('website_custom_menus').get(xmlId, null);
    }

    async onClickMenu(id, isApp, name = false) {
        const canProceed = await clearUncommittedChanges(this.env)
        if (canProceed) {
            if (isApp) {
                localStorage.setItem("cy_selected_app", id || false)
                this.state.currentSelectedApp = id
            } else {
                localStorage.setItem("cy_selected_menu", id || false)
                this.setCurrentSelectedMenu(id || false)
                if (id && name) {
                    let ids = this.recentApps.map(res => res["app_id"])
                    if (!ids.includes(id)) {
                        session.recent_app.unshift({
                            'app_id': id,
                            'name': name
                        });
                        session.recent_app.pop();
                        this.orm.create("recent.apps", [{
                            'app_id': id,
                            'user_id': session.uid,
                        }]);
                    }
                }
            }
            if (!id) {
                this.setCurrentSelectedMenu(false)
                this.state.isSidebarOn = true
                this.state.isApp = true
            } else {
                this.check = null
                if (isApp) {
                    this.state.isApp = false
                }
                this.state.isSidebarOn = true
                const menu = this.menuService.getMenuAsTree(id)
                const services = {
                    website: this.websiteService,
                    orm: this.orm,
                    dialog: this.dialog,
                    uiService: this.uiService
                };
                const menuConfig = this.get(menu.xmlid);
                if (menuConfig) {
                    this.state.isSidebarOn = false;
                    return menuConfig.openWidget ? menuConfig.openWidget(services) : this.dialog.add(menuConfig.Component, {
                        ...(menuConfig.getProps && menuConfig.getProps(services)),
                        ...menu.dynamicProps
                    });
                } else {
                    this.cyLeftSidebar.el.parentElement.classList.add('menuListFixed')
                    this.menuService.selectMenu(menu)
                    this.state.isSidebarOn = false;
                    let selectedMenu = this.menuService.getMenuAsTree(this.state.currentSelectedApp).name
                    localStorage.setItem("isSidebarOn", false)
                    localStorage.setItem("selectedAppName", selectedMenu || false)
                    this.state.selectedAppName = selectedMenu
                    const menuId = `#app_main${menu.id}`;
                    if (isApp) {
                        this.state.menus = this.menuService.getMenuAsTree(this.state.currentSelectedApp).childrenTree
                        this.cyLeftSidebar.el.querySelectorAll('.cy_active_main_menu').forEach(menu => menu.classList.remove('cy_active_main_menu'));
                        this.cyLeftSidebar.el.querySelectorAll('.cy_active_menu').forEach(menu => menu.classList.remove('cy_active_menu'));
                    }
                    const menuElement = this.cyLeftSidebar.el.querySelector(menuId);
                    if (menuElement) {
                        menuElement.classList.add('cy_active_main_menu');
                    }
//                    this.state.currentSelectedMenu = false;
                    this.env.bus.trigger("homeButtonClicked", {
                        isSubMenuOn: false
                    })
                    if (menu.name === 'Home') {
                        this.onClickLogo()
                    }
                }
            }
            const menuSearchInput = this.cyLeftSidebar.el.querySelector('input')
            if (menuSearchInput) {
                menuSearchInput.value = ''
                this.onKeyupSearch()
            }
        } else {
            this.notification.add(
                _t("You have unsaved changes. Save or discard them to continue."), {
                    type: "danger"
                }
            );
        }
    }

    setCurrentSelectedMenu(val) {
        this.state.currentSelectedMenu = val
    }

    onPin(id, name) {
        if (id && name) {
            if (!this.state.pinnedMenu.map(res => res["app_id"]).includes(id)) {
                this.state.pinnedMenu.unshift({
                    'app_id': id,
                    'name': name
                })
                this.orm.create("pinned.menu", [{
                    'app_id': id,
                    'user_id': session.uid,
                }]);
            }
        }
        var activeContextMenu = this.cyLeftSidebar.el.querySelectorAll('.context-menu[style="display: block;"]')
        activeContextMenu.forEach((menu) => {
            menu.style.display = 'none'
        })
    }

    onUnpin(id) {
        if (id) {
            this.state.pinnedMenu = this.state.pinnedMenu.filter(res => res["app_id"] != id)
            this.orm.call("pinned.menu", "unpin_menu", [id])
        }
        var activeContextMenu = this.cyLeftSidebar.el.querySelectorAll('.context-menu[style="display: block;"]')
        activeContextMenu.forEach((menu) => {
            menu.style.display = 'none'
        })
    }

    onClickMenuRecent(menuId) {
        let menu = this.menuService.getMenuAsTree(menuId)
        this.menuService.selectMenu(menu)
    }

    get recentApps() {
        return session.recent_app;
    }

    getMenus() {
        if (this.state.isApp) {
            return this.menuService.getApps()
        } else {
            let currentApp = {
                ...this.currentApp,
                avoidClick: true
            }
            return [currentApp, ...this.currentAppSections]
        }
        const menu = this.menuService.getMenuAsTree(this.state.currentSelectedMenu)
        this.menuService.selectMenu(menu)
    }

    get currentApp() {
        return this.menuService.getMenu(this.state.currentSelectedApp);
    }

    get currentAppSections() {
        return this.currentApp?.id
            ? this.menuService.getMenuAsTree(this.currentApp.id)?.childrenTree || []
            : [];
    }

    dropCheck(menu) {
        return !this.state.isApp && menu.childrenTree && menu.childrenTree.length != 0 && !menu.avoidClick
    }

    accordianMenuClick(ch_menu) {
        sessionStorage.removeItem("X2manyList")
        const menuId = `#menu${ch_menu.id}`;
        this.cyLeftSidebar.el.querySelectorAll('.cy_active_menu').forEach(menu => menu.classList.remove('cy_active_menu'));
        this.cyLeftSidebar.el.querySelector(menuId).classList.add('cy_active_menu');
        if (ch_menu.app_id) {
            this.onClickMenuRecent(ch_menu.app_id)
        } else {
            this.onClickMenu(ch_menu.id, false, ch_menu.name)
        }
    }
}

MenuSideBar.components = {
    Dropdown,
    DropdownItem
}

MenuSideBar.template = "cyllo_base.MenuSideBarNew"

ActionContainer.components = {
    ...ActionContainer.components,
    MenuSideBar
}

ActionContainer.template = xml`
<t t-name="web.ActionContainer">
  <div class="o_action_manager d-flex">
    <MenuSideBar/>
    <t t-if="info.Component" t-component="info.Component" className="'o_action'" t-props="info.componentProps" t-key="info.id"/>
  </div>
</t>`;
