function sendData() {
   var datePicker = document.getElementById('date-picker');
   var selectedDate = datePicker.value;
   var projectId = $("#project-select").val();
   if (projectId !== '') {
      if (selectedDate !== '') {
         // Отправка запроса с датой
         var date = $("#date-picker").val();
         $.ajax({
            type: "GET",
            url: "/logs?project_id=" + projectId + "&date=" + date,
            success: function (data) {
               fillTable(data)
            },
            error: function () {
               $("#log-table-body").empty(); // Очищаем содержимое tbody при ошибке
            },
         });
      } else {
         // Отправка запроса без даты
         $.ajax({
            type: "GET",
            url: "/logs?project_id=" + projectId,
            success: function (data) {
               fillTable(data)
            },
            error: function () {
               $("#log-table-body").empty();
            },
         });
      }
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