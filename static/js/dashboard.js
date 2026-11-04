const charts = JSON.parse(document.getElementById('charts').textContent);

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name);
const grid = {padding: {top: -20, right: 0, bottom: -4}, strokeDashArray: 4};

const types = {
    column: (data) => ({
        chart: {type: 'bar', stacked: true},
        plotOptions: {bar: {columnWidth: '50%'}},
        series: data.series,
        xaxis: {categories: data.labels},
        grid,
    }),
    hbar: (data) => ({
        chart: {type: 'bar'},
        plotOptions: {bar: {horizontal: true, barHeight: '50%'}},
        series: data.series,
        xaxis: {categories: data.labels},
        grid,
    }),
    donut: (data) => ({
        chart: {type: 'donut'},
        series: data.series[0].data,
        labels: data.labels,
        tooltip: {fillSeriesColor: false},
    }),
    heatmap: (data) => ({
        chart: {type: 'heatmap', background: 'transparent'},
        series: data.series,
        plotOptions: {heatmap: {radius: 3}},
        colors: [css('--tblr-chart-1')],
        stroke: {colors: [css('--tblr-bg-surface')]},
        theme: {mode: document.documentElement.dataset.bsTheme},
    }),
};

document.querySelectorAll('[data-chart]').forEach((el) => {
    const options = types[el.dataset.type](charts[el.dataset.chart]);
    options.chart = {
        ...options.chart,
        height: Number(el.dataset.height),
        fontFamily: 'inherit',
        parentHeightOffset: 0,
        toolbar: {show: false},
        animations: {enabled: false},
    };
    new ApexCharts(el, {
        dataLabels: {enabled: false},
        legend: {
            position: 'bottom',
            offsetY: 12,
            markers: {size: 5, strokeWidth: 0, shape: 'circle'},
            itemMargin: {horizontal: 8, vertical: 8},
        },
        ...options,
    }).render();
});

document.querySelectorAll('[data-table]').forEach((el) => {
    const valueNames = [...el.querySelectorAll('.table-sort')]
        .map((button) => ({name: button.dataset.sort, attr: 'data-sort'}));
    new List(el, {sortClass: 'table-sort', listClass: 'table-tbody', valueNames});
});
