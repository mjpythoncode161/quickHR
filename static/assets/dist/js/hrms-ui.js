/**
 * HRMS AdminLTE UI — Select2, DataTables (default features), list tables
 */
(function ($) {
  "use strict";

  function initSelect2() {
    if (!$.fn.select2) return;

    $("select.select2, form select.form-control:not(.no-select2)").each(function () {
      var $el = $(this);
      if ($el.closest("table").length) return;
      if ($el.hasClass("select2-hidden-accessible")) return;

      $el.select2({
        width: "100%",
        placeholder: $el.data("placeholder") || $el.find('option[value=""]').first().text() || "Select an option",
        allowClear: !$el.prop("required"),
        minimumResultsForSearch: 8,
      });
    });
  }

  function isEmptyListTable($table) {
    var $rows = $table.find("tbody tr");
    if ($rows.length === 0) return true;
    if ($rows.length === 1 && $rows.first().find("td[colspan]").length) return true;
    return false;
  }

  function prepareAppTables() {
    $(".content-wrapper table, .sa-admin-main table").each(function () {
      var $table = $(this);
      if ($table.hasClass("no-datatable") || $table.hasClass("roster-table")) return;
      if (!$table.find("thead").length) return;

      var colCount = $table.find("thead th").length;
      var isWideTable = $table.hasClass("hrms-datatable-wide") || colCount > 8;
      var tableClasses = "table-bordered table-striped table-hover mb-0 hrms-datatable sa-dash-table";
      if (!isWideTable) {
        tableClasses += " text-nowrap";
      }
      $table.removeClass("expandable-table hrms-hover-table").addClass(tableClasses);

      var $cardBody = $table.closest(".card-body");
      if ($cardBody.length) {
        $cardBody.removeClass("p-0").addClass("hrms-dt-card-body");
      }
    });

    $(".list-page .hrms-list-search-wrap").remove();
  }

  function initDataTables() {
    if (!$.fn.DataTable) return;

    var initCount = 0;
    var skipCount = 0;

    $(".content-wrapper table.hrms-datatable, .sa-admin-main table.hrms-datatable").each(function () {
      var $table = $(this);
      if ($table.hasClass("no-datatable")) {
        skipCount += 1;
        return;
      }
      if ($.fn.DataTable.isDataTable(this)) return;
      if (isEmptyListTable($table)) {
        skipCount += 1;
        return;
      }

      var isWide = $table.hasClass("hrms-datatable-wide") || $table.find("thead th").length > 8;
      if (isWide) {
        $table.removeClass("text-nowrap");
      }

      var $wrap = $table.parent(".table-responsive");
      if ($wrap.length && !isWide) {
        $table.detach().insertAfter($wrap);
        $wrap.remove();
      }

      var dtOptions = {
        responsive: true,
        autoWidth: false,
        pageLength: 10,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
        order: [],
        language: {
          search: "Search:",
          searchPlaceholder: "Search records...",
          lengthMenu: "Show _MENU_ entries",
          info: "Showing _START_ to _END_ of _TOTAL_ entries",
          infoEmpty: "Showing 0 to 0 of 0 entries",
          zeroRecords: "No matching records found",
          paginate: {
            first: "First",
            last: "Last",
            next: "Next",
            previous: "Previous",
          },
        },
      };

      if (isWide) {
        dtOptions.scrollX = true;
        dtOptions.columnDefs = [
          { responsivePriority: 1, targets: 1 },
          { responsivePriority: 2, targets: 2 },
          { responsivePriority: 3, targets: 6 },
          { responsivePriority: 4, targets: 0 },
          { responsivePriority: 5, targets: 3 },
          { responsivePriority: 6, targets: 4 },
          { responsivePriority: 10001, targets: [8, 9] },
          { responsivePriority: 10002, targets: [5, 7, 10] },
        ];
      }

      $table.DataTable(dtOptions);

      if (isWide && $wrap.length) {
        $wrap.addClass("hrms-dt-scroll-wrap");
      }

      initCount += 1;
    });

    // #region agent log
    fetch("http://127.0.0.1:7316/ingest/09fbde3a-4195-40e5-9b2b-c1f7f0fdf522", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "72a37d" },
      body: JSON.stringify({
        sessionId: "72a37d",
        location: "hrms-ui.js:initDataTables",
        message: "DataTables default init on list pages",
        data: {
          listPages: $(".list-page").length,
          appTables: $(".content-wrapper table.hrms-datatable, .sa-admin-main table.hrms-datatable").length,
          candidates: $(".content-wrapper table, .sa-admin-main table").length,
          initialized: initCount,
          skipped: skipCount,
          hasDataTablePlugin: !!$.fn.DataTable,
          attendanceTable: $("#attendanceTable").length,
          attendanceDtInit: $.fn.DataTable && $.fn.DataTable.isDataTable("#attendanceTable"),
        },
        timestamp: Date.now(),
        runId: "attendance-responsive",
        hypothesisId: "H1",
      }),
    }).catch(function () {});
    // #endregion
  }

  function logSidebarTypography() {
    var $mainLink = $(".hrms-app .nav-sidebar > .nav-item > .nav-link").first();
    var $subLink = $(".hrms-app .nav-sidebar .nav-treeview > .nav-item > .nav-link").first();
    var $brand = $(".hrms-app .main-sidebar .brand-text").first();
    var mainEl = $mainLink[0];
    var subEl = $subLink[0];
    var brandEl = $brand[0];
    // #region agent log
    fetch("http://127.0.0.1:7316/ingest/09fbde3a-4195-40e5-9b2b-c1f7f0fdf522", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "72a37d" },
      body: JSON.stringify({
        sessionId: "72a37d",
        location: "hrms-ui.js:logSidebarTypography",
        message: "sidebar medium font check",
        data: {
          hasSidebar: $(".hrms-app .main-sidebar").length > 0,
          expectedPrimary: "#172c78",
          sidebarBg: $(".hrms-app .main-sidebar")[0]
            ? getComputedStyle($(".hrms-app .main-sidebar")[0]).backgroundColor
            : null,
          topbarBg: $(".hrms-app .main-header")[0]
            ? getComputedStyle($(".hrms-app .main-header")[0]).backgroundColor
            : null,
          brandBg: $(".hrms-app .brand-link")[0]
            ? getComputedStyle($(".hrms-app .brand-link")[0]).backgroundColor
            : null,
          primaryBtnBg: $(".hrms-app .btn-primary").first()[0]
            ? getComputedStyle($(".hrms-app .btn-primary").first()[0]).backgroundColor
            : null,
          mainFontSize: mainEl ? getComputedStyle(mainEl).fontSize : null,
        },
        timestamp: Date.now(),
        runId: "theme-172c78",
        hypothesisId: "A-B-C-D",
      }),
    }).catch(function () {});
    // #endregion
  }

  function logPageSpacing() {
    var headerEl = $(".hrms-app .list-page .content-header")[0];
    var dashHeaderEl = $(".hrms-app .list-page .sa-dash-header")[0];
    var tdEl = $(".hrms-app .content-wrapper .hrms-datatable tbody td, .sa-admin-main .hrms-datatable tbody td").first()[0];
    var thEl = $(".hrms-app .content-wrapper .hrms-datatable thead th, .sa-admin-main .hrms-datatable thead th").first()[0];
    var cardBodyEl = $(".hrms-app .content-wrapper .hrms-dt-card-body, .sa-admin-main .hrms-dt-card-body").first()[0];
    var filterFormEl = $(".hrms-app .list-page .hrms-list-filter, .hrms-app .list-page .att-filter-form").first()[0];
    var dtRowEl = $(".hrms-app .list-page .dataTables_wrapper > .row").first()[0];
    // #region agent log
    fetch("http://127.0.0.1:7316/ingest/09fbde3a-4195-40e5-9b2b-c1f7f0fdf522", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "72a37d" },
      body: JSON.stringify({
        sessionId: "72a37d",
        location: "hrms-ui.js:logPageSpacing",
        message: "compact list table spacing check",
        data: {
          isListPage: $(".hrms-app .list-page").length > 0,
          appTableCount: $(".content-wrapper table.hrms-datatable, .sa-admin-main table.hrms-datatable").length,
          contentHeaderPaddingTop: headerEl ? getComputedStyle(headerEl).paddingTop : null,
          dashHeaderMarginBottom: dashHeaderEl ? getComputedStyle(dashHeaderEl).marginBottom : null,
          cardBodyPaddingTop: cardBodyEl ? getComputedStyle(cardBodyEl).paddingTop : null,
          filterFormMarginBottom: filterFormEl ? getComputedStyle(filterFormEl).marginBottom : null,
          dtRowMarginBottom: dtRowEl ? getComputedStyle(dtRowEl).marginBottom : null,
          tdPadding: tdEl ? getComputedStyle(tdEl).padding : null,
          thPadding: thEl ? getComputedStyle(thEl).padding : null,
          tdFontSize: tdEl ? getComputedStyle(tdEl).fontSize : null,
        },
        timestamp: Date.now(),
        runId: "compact-list-spacing",
        hypothesisId: "H1-H2-H3-H4",
      }),
    }).catch(function () {});
    // #endregion
  }

  function logAttendanceGridCells() {
    var woCell = $(".content-wrapper .attendance-grid-table td.hrms-att-wo, .content-wrapper .table td.hrms-att-wo").first()[0];
    // #region agent log
    fetch("http://127.0.0.1:7316/ingest/09fbde3a-4195-40e5-9b2b-c1f7f0fdf522", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "72a37d" },
      body: JSON.stringify({
        sessionId: "72a37d",
        location: "hrms-ui.js:logAttendanceGridCells",
        message: "attendance WO cell visibility check",
        data: {
          hasGrid: $(".attendance-grid-table").length > 0,
          woCellFound: !!woCell,
          woColor: woCell ? getComputedStyle(woCell).color : null,
          woBg: woCell ? getComputedStyle(woCell).backgroundColor : null,
          woText: woCell ? woCell.textContent.trim() : null,
        },
        timestamp: Date.now(),
        runId: "wo-visible-fix",
        hypothesisId: "H1-H2",
      }),
    }).catch(function () {});
    // #endregion
  }

  function logDashboardCards() {
    var statNum = $(".sa-dashboard-page .sa-stat-card .info-box-number").first()[0];
    var statText = $(".sa-dashboard-page .sa-stat-card .info-box-text").first()[0];
    // #region agent log
    fetch("http://127.0.0.1:7316/ingest/09fbde3a-4195-40e5-9b2b-c1f7f0fdf522", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "72a37d" },
      body: JSON.stringify({
        sessionId: "72a37d",
        location: "hrms-ui.js:logDashboardCards",
        message: "home dashboard stat card label bold check",
        data: {
          hasDashboard: $(".sa-dashboard-page").length > 0,
          statCardCount: $(".sa-stat-card").length,
          statTextFontWeight: statText ? getComputedStyle(statText).fontWeight : null,
          statTextColor: statText ? getComputedStyle(statText).color : null,
          statNumColor: statNum ? getComputedStyle(statNum).color : null,
        },
        timestamp: Date.now(),
        runId: "home-stat-label-bold",
        hypothesisId: "H1",
      }),
    }).catch(function () {});
    // #endregion
  }

  $(function () {
    initSelect2();
    prepareAppTables();
    initDataTables();
    logSidebarTypography();
    logPageSpacing();
    logAttendanceGridCells();
    logDashboardCards();
  });

  $(document).ajaxComplete(function () {
    initSelect2();
  });
})(jQuery);
