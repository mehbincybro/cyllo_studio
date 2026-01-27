/** @odoo-module **/
import { Component, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
const { DateTime } = luxon;
const COLORS = [
    "",
    "#FF9C9C",
    "#F7C698",
    "#FDE388",
    "#BBD7F8",
    "#D9A8CC",
    "#F8D6C8",
    "#89E1DB",
    "#97A6F9",
    "#FF9ECC",
    "#B7EDBE",
    "#E6DBFC"
];

export class GanttRenderer extends Component {
    setup() {
        this.archInfo = this.props.archInfo;
        this.model = this.props.list.resModel;
        this.fields = [
            'name',
            ...(this.archInfo.startDate ? [this.archInfo.startDate] : []),
            ...(this.archInfo.endDate ? [this.archInfo.endDate] : []),
            ...(this.archInfo.defaultGroup ? [this.archInfo.defaultGroup] : []),
            ...(this.archInfo.color ? [this.archInfo.color] : [])
        ];
        this.default_group = !!this.archInfo.defaultGroup;
        this.relatedModel = this.default_group && this.archInfo.relatedModels[this.model][this.archInfo.defaultGroup]?.relation;
        this.options = {};
        this.state = useState({
            tasks: [],
            groups: [],
        });
        this.ref = useRef('root-renderer');
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.generateGantt();
        this.current_window = {
            start: DateTime.now().startOf("week"),
            end: DateTime.now().endOf("week"),
        };
        this.displayDate = this.current_window.start.toFormat('yyyy-MM-dd') + " - " + this.current_window.end.toFormat('yyyy-MM-dd');
    }
    /**
    * For generating the gantt
    */
    async generateGantt() {
        const date = DateTime.now();
        this.groups = this.props.list.groupBy;
        // Checking The GroupBy is applied once
        if (this.groups.length > 1) {
             this.notification.add("Multiple Groups is not supported", { type: "danger", sticky: true, });
        };
        let values = await this.orm.searchRead(this.model, [], this.fields);
        values?.map(data => {
            return this.convertToLocal(data)
        });
        let records = await Promise.all(this.props.list.records.map(async (record) => {
            let id = record._values.id || record.evalContext.id;
            return {
                ...record._values,
                ...(await values.find(value => value.id === id))
            };
        }));
        this.records = records;
        this.showAllData = this.archInfo.showAllData == 'True';
        let result = await this.orm.searchRead(this.relatedModel, []);
        result = result.map(({ name, id, image_1920 }) => ({ id, name, image: image_1920 || null }));
        records.map(record => {
            record.image = result.find(item => item.id === record[this.archInfo.defaultGroup][0])?.image;
            return record;
        });
        if (this.showAllData && this.relatedModel) {
            records = records.length > 0
                      ? records.concat(result.filter(item => records.some(rec => rec[this.archInfo.defaultGroup][0] !== item.id)))
                      : result;
        };
        // Calling the 'CreateGroup()' method  for getting the groups
        this.CreateGroup(records);
        // Calling the 'CreateTasks()' method  for getting the tasks
        this.CreateTasks(records);
        // Getting the element that will display the Gantt view
        let container = this.ref.el.querySelector('#cyllo_gantt_widget');
        let $container = $(container);
        // Default: set the end and the start of the Gantt as the current week's start and end dates
        this.options.start = date.startOf("week").toISO();
        this.options.end = date.endOf("week").toISO();
        // Removing the zoomable function of the gantt
        this.options.zoomable = false;
        // Adding the horizontalScroll function of the gantt
        this.options.horizontalScroll = true;
        // Adding the verticalScroll function of the gantt
        this.options.verticalScroll = true;
        // Setting the timeline period on both side
        this.options.orientation = 'both';
        // Setting scale for the time axis.
        this.options.timeAxis = {scale: 'day', step: 1};
        this.options.editable = {
            add: this.archInfo.isLocked !== 'True' && this.archInfo.activeActions.create, // add new items by double tapping
            updateTime: this.archInfo.activeActions.edit, // drag items horizontally and update record
            updateGroup: this.archInfo.isLocked !== 'True' && this.archInfo.activeActions.editGroup, // drag items from one group to another
            remove: this.archInfo.isLocked !== 'True' && this.archInfo.activeActions.delete, // delete an item by tapping the delete button top right
        };
        /**
        * Opening the Wizard of the current record while double clicking on the bar
        */
        this.options.onUpdate = async (item, callback) => {
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: item.content,
                target: 'new',
                res_id: Number(item.id),
                res_model: this.model,
                views: [[false, 'form']],
            }, {
                onClose: async () => {
                    let record = await this.orm.searchRead(this.model, [['id', '=', item.id]], this.fields);
                    record?.map(data => {
                        let utcStartTime = DateTime.fromFormat(data[this.archInfo.startDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
                        let utcEndTime = DateTime.fromFormat(data[this.archInfo.endDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
                        data[this.archInfo.startDate] = utcStartTime.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
                        data[this.archInfo.endDate] = utcEndTime.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
                        data.image = result.find(item => item.id === data[this.archInfo.defaultGroup][0])?.image;
                    });
                    if (this.showAllData) {
                        this.CreateTasks(record);
                        callback(this.state.tasks);
                    } else {
                        this.records = this.records.map(task => task.id === record[0]?.id ? record[0] : task);
                        this.CreateGroup(this.records);
                        this.CreateTasks(this.records);
                        // Updates the view after updating record
                        this.timeline.setData({
                            groups: this.state.groups,
                        });
                        callback(this.state.tasks.filter(item => item.id === record[0]?.id)[0]);
                    }
                }
            });
        };
        /**
        * Creating the task while double-tapping on an empty space or just dragging on empty space
        */
        this.options.onAdd = (item, callback) => {
            let startDate = this.formatDateToString(item.start);
            let endDate = item.end ? this.formatDateToString(item.end) : startDate;
            this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: "New",
                target: 'new',
                res_model: this.model,
                views: [[false, 'form']],
                context: {
                    ['default_'+ this.archInfo.defaultGroup]: Number(item.group),
                    ['default_'+ this.archInfo.startDate]: startDate,
                    ['default_'+ this.archInfo.endDate]: endDate,
                }
            }, {
                onClose: async () => {
                    let record = await this.orm.searchRead(this.model, [], this.fields);
                    record = record.filter(item => !this.records.some(({id}) => id === item.id));
                    if (record.length > 0) {
                        record.map(data => {
                            let utcStartTime = DateTime.fromFormat(data[this.archInfo.startDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
                            let utcEndTime = DateTime.fromFormat(data[this.archInfo.endDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
                            data[this.archInfo.startDate] = utcStartTime.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
                            data[this.archInfo.endDate] = utcEndTime.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
                            data.image = result.find(item => item.id === data[this.archInfo.defaultGroup][0])?.image;
                        });
                        this.records.push(...record)
                        if (this.showAllData){
                            this.CreateTasks(record);
                            callback(this.state.tasks);
                        } else {
                            this.CreateGroup(this.records);
                            this.CreateTasks(this.records);
                            this.timeline.setData({
                                groups: this.state.groups.length > 0 ? this.state.groups : null,
                            });
                            callback(this.state.tasks.filter(item => item.id === record[0]?.id)[0]);
                        }
                    } else {
                        callback(null);
                    }
                }
            });
        };
        /**
        * Changing the time and group of the task while dragging the bar
        */
        this.options.onMove = async (item, callback) => {
            if (this.archInfo.isLocked) {
                let record = this.state.tasks.find(task => task.id === item.id);
                this.notification.add("Dragging is not allowed.", { type: "warning", sticky: false, });
                callback(record);
            } else if (this.is_grouped && (this.groups.length > 0 || this.default_group)) {
                let group = this.groups.length > 0 ? this.groups[0] : this.archInfo.defaultGroup;
                let record = await this.UpdateItemOnDrag(item, group);
                item.content = record.name;
                this.records.forEach(data => {
                    if (data.id === item.id) {
                        data.name = record.name;
                        if (record[this.archInfo.startDate]) {
                            let utcStartTime = DateTime.fromFormat(record[this.archInfo.startDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
                            data[this.archInfo.startDate] = utcStartTime?.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
                        }
                        if (record[[this.archInfo.endDate]]) {
                            let utcEndTime = DateTime.fromFormat(record[this.archInfo.endDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
                            data[this.archInfo.endDate] = utcEndTime?.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
                        }
                    }
                });
                callback(item);
            } else {
                this.orm.write(this.model, [Number(item.id)], {
                    [this.archInfo.startDate]: this.formatDateToString(item.start),
                    [this.archInfo.endDate]: this.formatDateToString(item.end)
                });
            };
        };
        /**
        * Unlink the task while clicking the delete button
        */
        this.options.onRemove = (item, callback) => {
            this.orm.unlink(this.model, [Number(item.id)]);
            this.records = this.records.filter(record => record.id !== item.id);
            if (!this.showAllData) {
                this.CreateGroup(this.records);
                this.CreateTasks(this.records);
                // Updates the view after deleting
                this.timeline.setData({
                    groups: this.state.groups,
                });
            }
            callback(item);
        };
        let items = new vis.DataSet(this.state.tasks);
        $container.empty();
        /**
        * Checking the attribute default_group_by has a date field if true, displaying the warning.
        */
        if (this.default_group_is_date) {
            this.default_group = false;
            this.default_group_is_date = false;
            this.notification.add("Date field is not supported to the attribute 'default_group_by'", { type: "danger", sticky: true, });
        };
        if (this.default_group || this.groups.length > 0) {
            // if the view is grouped passing the container, items, this.state.groups and  this.options as the arguments
            this.is_grouped = true;
            this.timeline = new vis.Timeline(container, items, this.state.groups, this.options);
        } else {
            // if the view is not grouped passing the container, items and  this.options as the arguments
            this.timeline = new vis.Timeline(container, items, this.options);
        };
        this.ref.el.querySelector('#view-selector').value = "Week";
    }
    /**
    * For updating the items value while dragging the item
    */
    async UpdateItemOnDrag(item, group) {
        let currentRecord = this.records.find(rec => rec.id === item.id);
        let startDate = new Date(currentRecord[this.archInfo.startDate]);
        let endDate = new Date(currentRecord[this.archInfo.startDate]);
        let data = {};
        if (item.start?.getTime() !== startDate?.getTime()) {
            data[this.archInfo.startDate] = this.formatDateToString(item.start);
        }
        if (item.end?.getTime() !== endDate?.getTime()) {
            data[this.archInfo.endDate] = this.formatDateToString(item.end);
        }
        if (item.group !== currentRecord[group][0]) {
           data[group] = item.group == 'x' ? false : item.group
        }
        await this.orm.write(this.model, [Number(item.id)], data)
        let record = await this.orm.searchRead(this.model, [['id', '=', item.id]], ['name']);
        return {...record[0], ...data}
    }
    /**
    * For getting the records in the current model and appending to the this.state.tasks
    */
    CreateTasks(records) {
        this.state.tasks = [];
        records.forEach((vals) => {
            let color = typeof vals[this.archInfo.color] === 'number' ? COLORS[vals[this.archInfo.color]] : vals[this.archInfo.color] || '#4368FA';
            let opacity = Math.round(Math.min(Math.max(0.5 || 1, 0), 1) * 255);
            let style = "background: repeating-linear-gradient(45deg, " + color + opacity.toString(16) + " 10px," + color + " 20px); min-height: 50px; display: flex; align-items: center;";
            let startDate = vals[this.archInfo.startDate];
            let endDate = vals[this.archInfo.endDate];
            let start = startDate ? this.formatDateTime(startDate) : null;
            let end = endDate ? this.formatDateTime(endDate) : null;
            let groupField = vals[this.archInfo.defaultGroup] || (this.showAllData ? [vals.id, vals.name, vals.image] : null);
            let group;
            // Check group applied in controller
            if (this.groups.length > 0) {
                let GroupField = vals[this.groups[0]];
                if (Array.isArray(GroupField) && GroupField.length === 2 && typeof (GroupField[1]) === 'string') {
                    // If group by field is M2o field
                    group = GroupField[0];
                } else if (typeof (GroupField) === 'string') {
                    // If group by field is Char field
                    group = this.state.groups.find(groupItem => groupItem.content === GroupField)?.id || 'x';
                } else if (!GroupField) {
                    // If the record have false value in the grouped field
                    group = 'x';
                };
            } else if (this.default_group) { // if the default_group_by is applied
                if (Array.isArray(groupField) && groupField.length === 2 && typeof (groupField[1]) === 'string') {
                    group = groupField[0];
                } else if (typeof (groupField) === 'string') {
                    group = this.state.groups.find(groupItem => groupItem.content === groupField)?.id || 'x';
                };
            };
            const found = this.state.tasks.some(item => item.id === vals.id);
            let task = {
              style,
              content: vals.name,
              id: vals.id,
              start,
              group,
            };
            if (start && !found) {
                endDate ? (task.end = end) : (task.editable = false);
                this.state.tasks.push(task);
            } else if (this.showAll) {
                this.state.tasks.push(task);
            };
        });
    }
    // For Generating the Groups
    CreateGroup(records) {
        this.state.groups = [];
        const processGroup = (groupField, isDefaultGroup = false) => {
            let obj = {
                content: null,
                style: 'min-width:200px; width: auto; justify-content:center; display:flex; min-height: 60px !important;',
                image: null
            };
            if (Array.isArray(groupField) && groupField.length === 3 && typeof (groupField[1]) === 'string') {
                obj.id = groupField[0];
                obj.content = groupField[1];
                obj.image = groupField[2];
                const found = this.state.groups.some(item => item.id === obj.id && item.content === obj.content);
                // Preventing duplicate entries
                if (!found) {
                    this.state.groups.push(obj);
                };
            } else if (typeof (groupField) === 'string') {
                obj.id = isDefaultGroup ? ++id : groupField;
                obj.content = groupField;
                const found = this.state.groups.some(item => item.content === obj.content);
                // Preventing duplicate entries
                if (!found) {
                    this.state.groups.push(obj);
                };
            };
        };
        let id = 0;
        if (this.groups.length > 0) {
            // Check group applied in controller
            if (this.groups[0].includes(':')) {
                // checking the group applied is date field, if true throwing displaying an error
                this.notification.add("Date is not supported", { type: "danger", sticky: true, })
                this.groups = []
                return
            };
            records.forEach((vals) => {
                let groupField = [...vals[this.groups[0]], vals.image];
                processGroup(groupField);
            });
        } else if (this.default_group) { // if the default_group_by is applied
            records.forEach((vals) => {
                let groupField = vals[this.archInfo.defaultGroup] ? [...vals[this.archInfo.defaultGroup], vals.image] : (this.showAllData ? [vals.id, vals.name, vals.image] : null);
                if (groupField && groupField.c) {
                    // Checking whether the field is a date
                    this.default_group_is_date = true;
                } else {
                    processGroup(groupField, true);
                };
            });
        };
    }
    // Formats a DateTime object into a string representation in the format 'YYYY-MM-DDTHH:mm:ss'.
    formatDateTime(dateTime) {
        if (typeof dateTime === 'string') {
            // If dateTime is a string
            const dateParts = dateTime.split(' ');
            const date = dateParts[0];
            const time = dateParts[1] ? dateParts[1] : '00:00:00';
            return `${date}T${time}`;
        } else {
            // If dateTime is a Luxon DateTime object wrapped in a Proxy
            const { year, month, day, hour, minute, second } = dateTime.c;
            return `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}T${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}:${second.toString().padStart(2, '0')}`;
        }
    }
    /**
    * Converting the UTC formate to local time
    */
    convertToLocal(data) {
        if (data[this.archInfo.startDate]) {
            let utcStartTime = DateTime.fromFormat(data[this.archInfo.startDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
            data[this.archInfo.startDate] = utcStartTime.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
        }
        if (data[this.archInfo.endDate]) {
            let utcEndTime = DateTime.fromFormat(data[this.archInfo.endDate], 'yyyy-MM-dd HH:mm:ss', { zone: 'utc' });
            data[this.archInfo.endDate] = utcEndTime.setZone(DateTime.now().zoneName).toFormat('yyyy-MM-dd HH:mm:ss');
        }
        return data;
    }
    /**
    * Converting the local time to UTC format for saving to database
    */
    formatDateToString(date) {
        return DateTime.fromJSDate(date, { zone: 'utc' }).toFormat('yyyy-MM-dd HH:mm:ss');
    }
    /**
    * Updating the view mode while switching the and displaying the current period of date.
    */
    updateViewMode(mode, date = DateTime.now()) {
        let startDate = date.startOf(mode);
        let endDate = date.endOf(mode);
        const timeAxisConfig = {
            'Day': { scale: 'hour', step: 1 },
            'Year': { scale: 'month', step: 1 },
            'default': { scale: 'day', step: 1 }
        };
        this.current_window.start = startDate.toISO();
        this.current_window.end = endDate.toISO();
        this.timeline.setOptions({
            timeAxis: timeAxisConfig[mode] || timeAxisConfig['default']
        });
        this.ref.el.querySelector('.currentDate').innerHTML = mode !== 'Day' ? `${startDate.toFormat('yyyy-MM-dd')} - ${endDate.toFormat('yyyy-MM-dd')}` : startDate.toFormat('yyyy-MM-dd');
        this.timeline.setWindow(this.current_window);
    }
    /**
    *  Changing the view range and displaying period while clicking the navigate buttons
    */
    UpdateDateRange(value, mode) {
        const startDateTime = DateTime.fromISO(this.current_window.start);
        const nextDate = value ? startDateTime.plus({ [mode]: 1 }) : startDateTime.minus({ [mode]: 1 });
        this.updateViewMode(mode, nextDate);
    }
}
GanttRenderer.template = 'cyllo_gantt.GanttRenderer';