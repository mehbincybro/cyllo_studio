/** @odoo-module **/
import { convertToTitleCase, ChartMaker } from "@cyllo_analytics/js/chart_maker"

QUnit.test("should return the chart options based on the provided data, dimension, measures, name, type, and dimension_axis", async function (assert) {
const data = [{ dimension: 'A', measure1: 10, measure2: 20 }];
const dimension = 'dimension';
const measures = ['measure1', 'measure2'];
const name = 'chart';
const type = 'bar';
const dimension_axis = 'x';
const chartMaker = new ChartMaker(data, dimension, measures, name, type, dimension_axis);
const expectedOptions = {
   title: {
       text: 'Chart'
   },
   legends: {
      data: ['chart']
   },
    legend: {
        type: 'scroll',
        orient: 'vertical',
        right: 10,
        top: 20,
        bottom: 20
    },
    xAxis: {
        data: ['A'],
        type: 'category'
    },
    yAxis: {
        type: 'value'
    },
    series: [
    {
        name: 'Measure1',
        type: 'bar',
        data: [10],
        emphasis: {
        label: {
           show: true,
           fontSize: 10
           }
        }
    },
    {
        name: 'Measure2',
        type: 'bar',
        data: [20],
        emphasis: {
            label: {
            show: true,
            fontSize: 10
            }
        }
    }
    ],
    tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b} : {c}'
    },
    grid: {
        left: '12%',
        right: '15%',
        top: '15%',
        bottom: '20%'
    },
    dataZoom: [
    {
        YAxisIndex: 0,
        end: 100,
        id: "insideY",
        moveOnMouseMove: true,
        moveOnMouseWheel: true,
        start: 30,
        type: "inside",
        zoomOnMouseWheel: false
        }
    ],
    };
    const options = chartMaker.makeGraphOptions();
    assert.deepEqual(options, expectedOptions);
});

QUnit.test('should convert a string with all lowercase letters to title case', (assert) => {
    const inputString = "hello";
    const expectedOutput = "hello";
    const actualOutput = convertToTitleCase(inputString);
    assert.equal(actualOutput, expectedOutput);
});