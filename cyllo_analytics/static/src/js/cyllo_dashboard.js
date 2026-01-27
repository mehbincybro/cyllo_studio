/** @odoo-module **/
import {registry} from "@web/core/registry";
import {useService, useBus} from "@web/core/utils/hooks";
const {Component, useRef, useState, onMounted, onWillStart, useEffect, status, useExternalListener} = owl;
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {ConfigurationDialog} from "./configuration_dialog";
import {MenuDialog} from "./menu_dialog_box";
import {DeleteDialog} from "./delete_dialog_box";
import {ThemeMaker} from "./theme_maker";
import {ExplainAIModal} from "./explain_with_ai/explain_with_ai_modal"
import {CyAnalyticMixin} from "@cyllo_analytics/js/mixin/cy_dashboard_mixin"
import {Many2XAutocomplete} from "@web/views/fields/relational_utils";
import {GraphTile} from "@cyllo_analytics/js/presentation/components/graph_tile";
import {useResize} from "@cyllo_base/js/hooks"
import {ControlPanel} from "@web/search/control_panel/control_panel";
import {KpiSheet} from "@cyllo_analytics/js/KpiSheet";
import {Table} from "@cyllo_analytics/js/table/table";
import {KpiSheetChart} from "@cyllo_analytics/js/kpi_sheet_chart";
import {_t} from "@web/core/l10n/translation";
import {SheetDeleteDialog} from "./cyllo_sheet";

export class CylloDashboard extends CyAnalyticMixin(Component) {
    /** Class for creating a dashboard component */
    setup() {
        super.setup();
        this.tourService = useService("tour_service");
        useResize("chart-container", this.resizeContainer.bind(this));
        this.filter_dropdown = useRef('filter_dropdown')
        this.graph = useRef('graph')
        this.container = useRef('chart-container')
        this.items = []
        this.dialogService = useService("dialog")
        this.notification = useService("notification")
        this.ui = useState(useService("ui"))
        this.vals = []
        this.chartImages = {}
        this.refreshObject = {
            refresh: false,
            currentLen: 0
        }
        useBus(this.env.bus, "SIDEBAR_MENU_TOGGLE", ({detail:{isSidebarOn}}) => {
            /*
            * To Resize the charts when the menu is toggled
            * */
            if (!this.state.originalWidth) {
                this.state.originalWidth = this.state.width
            }
            const ref = this.__owl__.bdom.parentEl
            const {width} = ref.getBoundingClientRect()
            const adjWidth = (width * 0.95) / 12
            this.state.width = isSidebarOn ? this.state.originalWidth : adjWidth
            setTimeout(() => {
                if (status(this) !== "destroyed") {
                    this.env.bus.trigger("REFRESH_GRAPH") //Force Render
                }
            }, 100)
        })
        useEffect(() => {
            this.env.bus.trigger("REFRESH_GRAPH")
        }, () => [this.state.width, this.ui.size]);
        useEffect(() => {
            const bannerEl = this.dashboard.el.querySelector('.o_pj_dashboard');
            var root = document.querySelector(':root');
            if (this.bannerState.banner.length) {
                const {
                    image_1920
                } = this.bannerState.banner[0];
                if (!image_1920) {
                    return root?.style.setProperty('--banner-image-url', `url('')`);
                }
                const imageUri = `data:image/svg+xml;base64,${image_1920}`;
                fetch(imageUri)
                    .then(response => response.text())
                    .then(svgData => {
                        const parser = new DOMParser();
                        const svgDoc = parser.parseFromString(svgData, 'image/svg+xml');
                        var {
                            theme_color_ids: newColors, title
                        } = this.themeState.theme
                        newColors = newColors.slice(1, newColors.length - 1);
                        for (let i = 0; i <= 7; i++) {
                            const circles = svgDoc.querySelectorAll(`.st${i}`);
                            if (circles.length) {
                                circles.forEach((circle) => {
                                    var index = i >= newColors.length ? Math.floor(Math.random() * newColors.length) : i;
                                    var color = newColors[index] == title ? newColors[Math.floor(Math.random() * newColors.length)] : newColors[index]
                                    circle.style.fill = color;
                                });
                            }
                        }
                        const serializedSvg = new XMLSerializer().serializeToString(svgDoc);
                        const modifiedImageUri = `data:image/svg+xml;base64,${btoa(serializedSvg)}`;
                        root?.style.setProperty('--banner-image-url', `url(${modifiedImageUri})`);
                    })
                    .catch(error => {
                        console.error('Error fetching SVG data:', error);
                    });
            } else {
                root?.style.setProperty('--banner-image-url', `url('')`);
            }
        }, () => [this.bannerState.banner, this.themeState.theme?.theme_color_ids]);

        this.is_subAction = this.props.action.context.is_subAction || false;
        onMounted(async () => {
            this.state.globalFilters = await this.orm.searchRead('dashboard.global.filter', [
                ['dashboard_config_id', '=', this.id]
            ])
            if (!this.sortedItems.length && !this.is_subAction) {
                this.state.showInfo = true;
            }
        })
        onWillStart(async () => {
            this.state.sources = await this.orm.searchRead('dashboard.config', [])
        })
        this.positions = {
            x: 0,
            y: 0,
            w: 0,
            h: 0,
            ft: true,
            maxH: [],
            maxHVal: {0: [0]},
            cache: {}
        }
        this.firstLine = true
        useEffect(() => {
            this.dashboard.el.style.backgroundColor = this.themeState.theme.background
            if (this.ui.size > 3) {
                var setTemplateId = setTimeout(() => {
                    if (this.hasAccess) {
                        this.onSetTemplate()
                    }
                }, 3000)
                return () => {
                    clearTimeout(setTemplateId)
                }
            }
        }, () => [this.themeState.theme])
    }

    closeFilterSidebar() {
        if (this.isSearchMode) return;
        this.state.optionClass = 'collapse-filter'
        this.state.options = []
        this.state.currentItem = false
    }

    get isSearchMode() {
        return Boolean(this.state.search.length)
    }

    get opacityClass() {
        return this.state.showInfo ? "opacity-d" : "opacity-u";
    }

    async onSetTemplate() {
        if (!this.graph.el) return
        const element = this.graph.el.querySelector(".cy_dash-card_container")
        const canvas = await html2canvas(element)
        let imgData = canvas.toDataURL('image/png');
        if (status(this) !== "destroyed") {
            this.orm.write("dashboard.config", [this.id], {
                image_1920: imgData.split(',')[1]
            })
        } else {
            console.warn("Couldn't capture the template")
        }
    }

    resizeContainer(width) {
        this.state.width = width / 12;
    }

    getDate(key) {
        return this.timFrameState[`date_${key}`]
    }

    setCustomDate(id, value) {
        const date = moment(value).format(this.dateFormats.actual)
        var id_o = id === "date_0" ? "date_1" : "date_0"
        if ((id == "date_0" && date > this.timFrameState[id_o]) || (id == "date_1" && date < this.timFrameState[id_o])) {
            this.notification.add(_t("The start date cannot be greater than the end date"), {
                type: "warning",
            });
            return;
        }
        this.timFrameState[id] = date
        var key = id === "date_0" ? "start-date" : "end-date"
        this.filters[key] = date
    }

    get timFrameDisplayName() {
        for (const [key, value] of Object.entries(this.TimeFrame)) {
            if (value === this.timFrameState.selected) return key
        }
    }

    timeFrameChange(ev) {
        var value = ev.target.value
        this.timFrameState.selected = value
        if (value !== "custom") {
            var flag = !['quarter_l', 'month_l', 'year_l'].includes(value)
            value = value.split("_")[0]
            this.dateOrder(flag, value)
        }
    }

    sourceDashboard(dashboard) {
        this.actionService.doAction({
            target: "current",
            tag: "cy_analytic_dashboard",
            type: "ir.actions.client",
            context: {
                rec_id: dashboard.id
            }
        })
    }

    /**
     * Fetch data for the dashboard.
     */
    fetchData() {
    }

    /**
     * Explain the dashboard with AI.
     * @returns {Promise} - A promise for performing the action.
     */
    explainWithAI(options) {
        this.dialogService.add(ExplainAIModal, {
            options,
            theme: this.themeState.theme,
            currentTheme: this.themeState.currentTheme,
            isDarkMode: this.state.darkMode
        })
    }

    computeStyle(item) {
        const isSearch = Boolean(this.state.search.length)
        const unit = this.state.width
        const toggleClass = 'chart-container-absolute'
        const sheetPosition = item.dashboard_sheet_option_ids
        let graph_height, graph_width, x, y
        const {height, width} = this.getChartSizes(item.type)
        if (item.id in this.positions.cache && !isSearch) {
            ({
                graph_height,
                graph_width,
                x,
                y
            } = this.positions.cache[item.id])
        } else {

            if (sheetPosition?.length && !isSearch) {
                ({
                    graph_height,
                    graph_width,
                    x,
                    y
                } = sheetPosition[0].attributes)
                if (this.positions.w && !x) {
                    this.positions.w = 0
                }
            } else {
                if (isSearch) {
                    if (sheetPosition.length) {
                        ({
                            graph_height,
                            graph_width,
                        } = sheetPosition[0].attributes)
                    } else {
                        graph_height = height
                        graph_width = width
                    }

                } else {
                    graph_height = height
                    graph_width = width
                }
                x = this.positions.w + graph_width > 12 ? 0 : this.positions.w
                if (this.positions.w && !x) {
                    this.positions.w = 0
                    const newY = this.positions.maxHVal[this.positions.y]
                    y = Math.max(...newY) + this.positions.y
                } else {
                    y = this.positions.y
                    const allY = Object.entries(this.positions.maxHVal)
                        .filter(([key]) => parseInt(key, 10) !== y)
                        .flatMap(([key, items]) =>
                            items.map(item => item + parseInt(key, 10))
                        );
                    const isAnyGreaterThanY = allY.some(value => value > y);
                    if (isAnyGreaterThanY) {
                        y = Math.max(...allY)
                        x = 0
                        this.positions.w = 0
                    }
                }
            }
            this.positions.x = x
            this.positions.y = y
            this.positions.w += graph_width
            this.positions.h = graph_height
            if (this.positions.maxHVal[y]) {
                this.positions.maxHVal[y].push(graph_height)
            } else this.positions.maxHVal[y] = [graph_height]
            if (!sheetPosition?.length && !(item.id in this.positions.cache)) {
                this.orm.call("dashboard.sheet", "set_sheet_position", [item.id, this.id], {
                    x,
                    y,
                    graph_width,
                    graph_height
                })
            }
        }

        const attributes = {
            graph_height,
            graph_width,
            x,
            y
        }
        this.positions.cache[item.id] = attributes
        const style = {
            height: `${(graph_height * unit) - 10}px;`,
            width: `${(graph_width * unit) - 10}px;`,
            top: `${y * unit}px;`,
            left: `${x * unit}px;`,
        }
        this.refreshObject.currentLen++
        return {
            style,
            toggleClass,
            attributes
        }
    }

    /**
     * Edit the dashboard.
     * @returns {Promise} - A promise for performing the action.
     */
    onEdit() {
        if (this.state.showInfo) return;
        return this.actionService.doAction({
            target: "current",
            tag: "edit_dashboard",
            type: "ir.actions.client",
            context: {
                rec_id: this.id
            }
        })
    }

    openRecord(kpi, item) {
        var {
            filter_ids,
            sheet_filter_ids
        } = item
        var domain = [];
        for (const {
            global_filter_id: {
                code,
                operator
            },
            field
        }
            of sheet_filter_ids) {
            if (this.filters[code])
                domain.push([field.split('.')[1], operator, this.filters[code]])
        }
        filter_ids = filter_ids.filter(item => item.is_active)
        for (const {
            domain: filterD
        }
            of filter_ids) {
            const subD = filterD.split(" OR ").map(item => {
                const match = item.match(/^(.*?)\s*(=|!=|>|<|>=|<=|IN|NOT\s+IN)\s*(.*)$/);
                const lhs = match[1].trim().split(".")[1];
                const opr = match[2].trim().toLowerCase();
                let rhs = match[3].trim();
                if (rhs.startsWith("'") && rhs.endsWith("'")) {
                    rhs = rhs.slice(1, -1);
                }
                if (rhs.includes('(') && rhs.includes(')')) {
                    rhs = rhs.replace(/\(/g, '[').replace(/\)/g, ']');
                    rhs = eval(rhs);
                }
                domain.unshift('|');
                return [lhs, opr, rhs];
            })
            domain.push(...subD);
        }
        return this.actionService.doAction({
            name: _t("My Dashboard"),
            type: 'ir.actions.act_window',
            res_model: kpi.model,
            view_mode: 'tree,form,calendar',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            domain,
            target: 'current',
        });
    }

    hideDropdown() {
        var sheet_conf = this.graph.el.querySelector('.stack-item').querySelectorAll('.dropdown')
        for (const elem of sheet_conf) {
            if (!elem.style.display) {
                elem.style.display = 'none';
            } else {
                elem.style.display = 'block';
            }
        }
    }

    exportPDF(type) {
        const cutoffImage = (image, rowsToCut, pageHeight) => {
            var imagePieces = [];
            var widthOfOnePiece = image.width;
            var heightOfOnePiece = pageHeight || image.height / rowsToCut;
            for (var x = 0; x < 1; ++x) {
                for (var y = 0; y < rowsToCut; ++y) {
                    var canvas = document.createElement('canvas');
                    canvas.width = widthOfOnePiece;
                    canvas.height = heightOfOnePiece;
                    var context = canvas.getContext('2d');
                    context.drawImage(
                        image,
                        x * widthOfOnePiece,
                        y * heightOfOnePiece,
                        widthOfOnePiece,
                        heightOfOnePiece,
                        0,
                        0,
                        canvas.width,
                        canvas.height
                    );
                    imagePieces.push(canvas.toDataURL('image/png'));
                }
            }

            return imagePieces;
        };
        var element = this.graph.el.querySelector('.stack-item');
        element.querySelectorAll('.chart-container-absolute').forEach((item) => {
            item.classList.add('print-card')
        })
        this.hideDropdown();
        let pdf = new jsPDF(type, 'mm', 'a4');
        html2canvas(element, {
            scale: 1.2,
            allowTaint: true,
            useCORS: true,
            logging: false,
            scrollY: -window.scrollY, // Capture the entire scrollable area
            windowHeight: element.scrollHeight + 1000,
            ignoreElements: (node) => node.classList.contains('ai-btn-class')
        }).then((canvas) => {
            let imgData = canvas.toDataURL('image/png');
            let pageWidth = pdf.internal.pageSize.getWidth();
            let pageHeight = pdf.internal.pageSize.getHeight();
            let imageWidth = pageWidth - 25;
            let imageHeight = (imageWidth / canvas.width) * canvas.height;
            let offsetX = 12;
            let offsetY = 15;
            var pdfPages = Math.ceil(imageHeight / pageHeight);
            var value = 2850
            if (type === 'l') {
                imageWidth = pageWidth - 100
                offsetX = 50;
                pdfPages = Math.ceil(imageHeight / 250);
                value = 2000
            }
            const canvasData = cutoffImage(canvas, pdfPages, value)
            for (let i = 0; i < pdfPages; i++) {
                const pieceOffsetY = i * pageHeight;
                var pieceHeight = 250;
                const pieceImgData = canvasData[i];
                if (i === 0) {
                    pdf.setFont("helvetica");
                    pdf.setFontType("bold");
                    pdf.setFontSize(9);
                    pdf.text(`${this.name} - This Dashboard Shows Information From ${this.filterData.date_0} To ${this.filterData.date_1}.`, offsetX, 10);
                }
                if (i > 0) {
                    offsetY = 2;
                    pdf.addPage();
                }
                pdf.addImage(pieceImgData, 'PNG', offsetX, offsetY, imageWidth, -pieceHeight);
            }
            this.hideDropdown();
            pdf.save(this.name);
            element.querySelectorAll('.chart-container-absolute').forEach((item) => {
                item.classList.remove('print-card')
            })
        });
    }

    /**
     * Export the dashboard data to JSON.
     */
    async onJsonExport() {
        try {
            const data = await this.orm.call("dashboard.config", "get_dashboard_data", [this.id]);
            const json = JSON.stringify(data);
            const blob = new Blob([json], {
                type: "application/json"
            });
            const url = URL.createObjectURL(blob);
            const file = document.createElement("a"); // Correct the element type to "a"
            file.download = this.name + " dashboard.json";
            file.href = url;
            file.click();
        } catch (error) {
            console.error("An error occurred:", error);
        }
    }

    /**
     * Add the dashboard to the menu. */
    onAddToMenu() {
        this.dialogService.add(MenuDialog, {
            rec_id: this.id,
            name: this.name
        })
    }

    /**
     * Delete the dashboard.
     */
    onDelete() {
        this.dialogService.add(DeleteDialog, {
            body: `Are You Sure you Want To Delete, ${this.state.name} Dashboard?`,
            id: this.id,
            removeManually: this.removeManually.bind(),
            model: 'dashboard.config'
        })
    }

    /**
     * Configure the dashboard.
     */
    onConfig() {
        this.dialogService.add(ConfigurationDialog, {
            id: this.id,
            name: this.props.name,
            applyTheme: this.switchTheme.bind(this),
            onClickSave: this.onConfigSave.bind(this),
        })
    }

    /**
     * Present the dashboard.
     * @returns {Promise} - A promise for performing the action.
     */
    onPresent() {
        if (this.state.showInfo) return;
        return this.actionService.doAction({
            target: "current",
            tag: "present_selection",
            type: "ir.actions.client",
            context: {
                rec_id: this.id
            }
        })
    }

    /**
     * Select a theme.
     * @param {number} themeId - The ID of the selected theme.
     */
    async OnSelectTheme(themeId) {
        this.themeState.theme_id = themeId
        await this.orm.write("dashboard.config", [this.id], {
            theme_id: themeId
        })
        this.applyTheme()
    }

    /**
     * Apply the selected theme.
     */
    async applyTheme() {
        this.themeState.theme = await this.orm.call("dashboard.theme", "read_theme",
            [this.themeState.theme_id]
        )
        var theme_maker = new ThemeMaker(this.themeState.theme)
        this.themeState.currentTheme = theme_maker.getTheme()
    }

    /**
     * Switch the theme.
     * @param {number} themeId - The ID of the theme to switch to.
     */
    switchTheme(themeId) {
        this.themeState.theme_id = themeId
        this.applyTheme()
    }

    /**
     * Add a graph to the dashboard.
     * @returns {Promise} - A promise for performing the action.
     */
    addGraph() {
        return this.actionService.doAction({
            target: "current",
            tag: "cy_analytic_sheet",
            type: "ir.actions.client",
            context: {
                dashboard_id: this.id,
                display_name: this.name
            }
        })
    }

    onEditSheet(sheet) {
        return this.actionService.doAction({
            target: "current",
            tag: "cy_analytic_sheet",
            type: "ir.actions.client",
            context: {
                rec_id: sheet.id
            }
        })
    }

    onDeleteSheet(sheet) {
        this.dialogService.add(SheetDeleteDialog, {
            id: sheet.id,
            model: "dashboard.sheet",
            body: `Are You Sure you Want To Delete ${sheet.name} ?`,
            removeManually: () => {
                var index = this.state.sortedItems.indexOf(sheet)
                this.state.sortedItems.splice(index, 1)
                if (!this.state.sortedItems.length) {
                    this.state.showInfo = true;
                }
            }
        })
    }

    onHideSheet(sheet) {
        this.dialogService.add(SheetDeleteDialog, {
            title: 'Hide',
            body: `Are You Sure you Want To Hide ${sheet.name} From Dashboard ${this.name} ?`,
            callBackAction: () => {
                var index = this.state.sortedItems.indexOf(sheet)
                this.state.sortedItems.splice(index, 1)
                if (!this.state.sortedItems.length) {
                    this.state.showInfo = true;
                }
                this.orm.call("dashboard.config", "remove_sheet", [this.id, sheet.id])
            }
        })

    }

    async onConfigSave(changes) {
        if (changes.name) {
            this.state.name = changes.name
        }
        if (Object.keys(changes).includes("banner_id")) {
            if (changes.banner_id) {
                this.bannerState.banner = await this.orm.read('dashboard.banner', [changes.banner_id])
            } else this.bannerState.banner = [];
        }

    }

    exportAsPNG(sheet) {
        const imgSrc = this.chartImages[sheet.id]
        const downloadLink = document.createElement('a');
        downloadLink.href = imgSrc;
        downloadLink.download = sheet.name;
        downloadLink.click();
    }

    filterClose() {
        this.filter_dropdown.el.classList.remove('show');
    }

    setImage(img, name, id) {
        this.chartImages[id] = img;
    }

    getDomain(filter) {
        let ids = this.filters[filter.code] || []
        return [
            ['id', 'not in', ids]
        ]
    }

    onRemoveFilter(rec, filter) {
        let indexTimFrameState = this.timFrameState[filter.code].indexOf(rec)
        let indexFilters = this.filters[filter.code].indexOf(rec)
        this.timFrameState[filter.code].splice(indexTimFrameState, 1)
        this.filters[filter.code].splice(indexFilters, 1)
    }

    async onSelect(ev, filter) {
        if (filter.type == 'datetime') {
            this.timFrameState.selected = 'custom'
            var {
                value
            } = ev.target
            var id = ev.target.getAttribute('id')
            this.setCustomDate(id, value)
        }
        if (filter.type == 'many2one') {
            if (!this.timFrameState[filter.code]) {
                this.timFrameState[filter.code] = [];
            }
            var res = await this.orm.read(filter.relation, [ev[0].id], ["display_name"]);
            if (!this.timFrameState[filter.code].includes(res[0])) {
                this.timFrameState[filter.code].push(res[0]);
            }
            if (!this.filters[filter.code]) {
                this.filters[filter.code] = [];
            }
            if (!this.filters[filter.code].includes(ev[0].id)) {
                this.filters[filter.code].push(ev[0].id);
            }
        }
    }

    closeFilter() {
        this.filter_dropdown.el.classList.add("cy_filter_toggler")
        this.dashboard.el.querySelector(".cy-churn-filter-btn").classList.remove("show")
    }

    onClickFilter() {
        this.filter_dropdown.el.classList.toggle("cy_filter_toggler")
        this.dashboard.el.querySelector(".cy-churn-filter-btn").classList.toggle("show")
    }

    applyFilter() {
        Object.assign(this.filterData, {
            ...JSON.parse(JSON.stringify(this.timFrameState)),
            date_0: this.timFrameState.date_0.replace(/-/g, '/'),
            date_1: this.timFrameState.date_1.replace(/-/g, '/'),
        });
        this.storeDefaultFilter();
        this.applyAllFilters();
        this.closeFilter()
    }

    onClickChart(item, index) {
        if (index === this.state.currentItem) {
            this.state.optionClass = 'collapse-filter'
            this.state.options = []
            this.state.currentItem = false
        } else {
            this.state.options = item.filter_ids
            this.state.currentItem = index
            this.state.optionClass = ''
        }
    }

    filterChange(option, index) {
        option.is_active = !option.is_active
        this.applyItemFilter(this.state.sortedItems[index])
    }

    get filterInfo() {
        return owl.markup(
            "The Global Filter applies based on the fields defined in the sheet editor's global filter section." +
            "<br/><br/>" +
            `To change default filter fields;<br/>Click "Edit" in dropdown menu of the charts, then go to Global Filter and modify the corresponding fields.`
        );
    }
}

// Define the components used in the CylloDashboard
CylloDashboard.components = {
    Dropdown,
    DropdownItem,
    GraphTile,
    ControlPanel,
    Many2XAutocomplete,
    KpiSheet,
    KpiSheetChart,
    Table
}
// Define the template for the CylloDashboard
CylloDashboard.template = "cyllo_analytics.CylloDashboard";
// Register the cyllo_analytics component in the actions category
registry.category("actions").add("cy_analytic_dashboard", CylloDashboard);