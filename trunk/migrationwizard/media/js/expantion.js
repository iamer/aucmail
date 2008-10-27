// JavaScript Document
$(document).ready(function(){

		  
			  $('.block-expansion-button').click( function() { 
													 style = $('#on-expande').css('display');
														
													 	if (style == 'block')  {
															$('#on-expande').css('display','none') ;
														}
														else {
															$('#on-expande').css('display','block') ;
															$('#on-expande-error').css('display','none') ;
														}
													 
													 
				});
        $('input[@id=error-log]').click( function(){
                           style = $('#on-expande-error').attr('style');
													 if (style) {
													 	at = style.split(':');
														
													 	if (at[1] == ' block;')  {
															$('#on-expande-error').attr('style','display:none') ;
														}
														else {
															$('#on-expande-error').attr('style','display:block') ;
															$('#on-expande').attr('style','display:none') ;
														}
													 }
													 else {
													   $('#on-expande-error').attr('style','display:block') ;
														$('#on-expande').attr('style','display:none') ;
													 }

        });
 });

