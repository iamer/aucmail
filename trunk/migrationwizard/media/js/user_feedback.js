
$().ready(function(){
    $('form[@id=feedback-form]').submit(function () {
            var text = $('textarea[@id=feedback-textarea]').attr('value');
            if ((text == '') || (text.match(/^[\s]*$/))) {
                 $('div[@id=submitted-feedback-form]').css('display','none');
                 $('div[@id=unsubmitted-feedback-form]').css('display','block');
                 return false;
            }

            $.post('/wizard/feedback/', { feedback : text } , function(data) {
              if(data && data == 'done'){
                 $('div[@id=submitted-feedback-form]').css('display','block');
                 $('div[@id=unsubmitted-feedback-form]').css('display','none');
              } else if(!data || (data && data == 'failed')){
                 $('div[@id=submitted-feedback-form]').css('display','none');
                 $('div[@id=unsubmitted-feedback-form]').css('display','block');
              } 
              })
      
    return false;
    })
})
