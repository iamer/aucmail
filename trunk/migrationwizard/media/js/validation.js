$().ready(function() {
  $('input[@class=submit-button]').click(function () {
    var search_field = $('input[@name=search_item]');
      if ((search_field.attr('value') == '') || (search_field.attr('value').match(/^[\s]*$/))) {
        if ($('label[@class=search_error]').length == 0) {
          $('div[@id=search_item]').append('<label class=search_error>You must enter the user name</label>');
        }
        return false;
      }
  });
  var checked = ''
  $('input[@id=change_status]').click(function () {
    $('input[@id=check_user_status]').each(function () {
      if (($(this).attr('checked'))) { 
        checked = 'true';
      }
    });
    if (checked != 'true'){
      alert("You must check the user(s) that you want to change");
      return false;
    }
  });
  $('input[@name=check_all]').click( function () {
    if ($(this).attr('checked')) {
      $('input[@id=check_user_status]').each(function () {
        $(this).attr('checked','checked');
      });
      }
      else if (!($(this).attr('checked'))) {
      $('input[@id=check_user_status]').each(function () {
        $(this).attr('checked','');
      });
      }
  });
});
