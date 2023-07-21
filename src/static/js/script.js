$(function () {
   moment.locale("ru"); // Если требуется локализация на русский язык
   // Инициализируем daterangepicker
   $("#date-range-picker").daterangepicker({
      startDate: moment().subtract(29, "days"), // Начальная дата (последние 30 дней)
      endDate: moment(), // Конечная дата (сегодня)
      maxDate: new Date(),
      // Задаем пресеты для дат
      ranges: {
         Сегодня: [moment(), moment()],
         Вчера: [moment().subtract(1, "days"), moment().subtract(1, "days")],
         "Последние 7 дней": [moment().subtract(6, "days"), moment()],
         "Последние 30 дней": [moment().subtract(29, "days"), moment()],
         "Этот месяц": [moment().startOf("month"), moment().endOf("month")],
      },
      // Форматируем календарь
      locale: {
         format: "DD.MM.YYYY",
         separator: " - ",
         applyLabel: "Применить",
         cancelLabel: "Отменить",
         fromLabel: "От",
         toLabel: "До",
         customRangeLabel: "Своя дата",
      },
   });
});

function sendData() {
   // Обработка входных данных и отправка запроса
   var datePicker = $("#date-range-picker").data("daterangepicker");
   var projectId = $("#project-select").val();
   if (projectId !== "") {
      var startDate = datePicker.startDate.format("YYYY-MM-DD");
      var endDate = datePicker.endDate.format("YYYY-MM-DD");
      // Отправляем запрос на сервер с выбранным проектом и периодом дат
      $.ajax({
         type: "GET",
         url:
            "/logs?project_id=" +
            projectId +
            "&startDate=" +
            startDate +
            "&endDate=" +
            endDate,
         success: function (data) {
            fillTable(data);
         },
         error: function () {
            $("#log-table-body").empty(); // Очищаем содержимое tbody при ошибке
         },
      });
   } else {
      // Очистить таблицу, если никакой проект не выбран
      $("#log-table-body").empty();
   }
}

function fillTable(data) {
   var logs = JSON.parse(data);
   var tbody = $("#log-table-body");
   // Очистить содержимое tbody перед добавлением новых записей
   tbody.empty();
   for (var i = 0; i < logs.length; i++) {
      var log = logs[i];
      var row =
         "<tr>" +
         "<td>" +
         (i + 1) +
         "</td>" +
         "<td>" +
         log.user_name +
         "</td>" +
         "<td>" +
         log.user_id +
         "</td>" +
         "<td><a href='" +
         log.task_link +
         "'>" +
         log.task +
         "</a></td>" +
         "<td>" +
         log.datetime_creating +
         "</td>" +
         "</tr>";
      tbody.append(row); // Добавить новую запись в tbody
   }
}
