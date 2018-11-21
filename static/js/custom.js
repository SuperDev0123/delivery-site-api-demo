function toggle(source) {
  checkboxes = document.getElementsByName('chk');
  for(var i=0, n=checkboxes.length;i<n;i++) {
    checkboxes[i].checked = source.checked;
  }
}

$(document).ready(function(){
    $('[data-toggle="popover"]').popover(); 
});

// When the user clicks on div, open the popup
function myFunction() {
    var popup = document.getElementById("myPopup");
    popup.classList.toggle("show");
}