$().ready(function(){
    $('form[@id=mobile-form]').submit(function () {
      var mobile = $('input[@id=phone-num]').attr('value');
      var reg = '01[0-9]{8}';
      if ((!mobile.match(/^01[0-9]{8}$/))){
        $('div[@id=valid-num]').css('display','none');
        $('div[@id=invalid-num]').css('display','block');
      }
      else {
            $.post('/wizard/submit_mobile/', { num : mobile } , function(data) {
              if(data == 'valid'){
                 $('div[@id=valid-num]').css('display','block');
                 $('div[@id=invalid-num]').css('display','none');

              } else if(data == 'invalid'){
                 $('div[@id=valid-num]').css('display','none');
                 $('div[@id=invalid-num]').css('display','block');
              }    
              })
      }
    return false;
    })
})
