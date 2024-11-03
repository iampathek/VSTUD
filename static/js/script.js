function openNav() {
    var sidebar = document.getElementById("sidebar");
    var overlay = document.getElementById("overlay");
    overlay.style.display="block"
    sidebar.style.left="0px"
    sidebar.style.zIndex="10";
}
function closeNav() {
    var sidebar = document.getElementById("sidebar");
    var overlay = document.getElementById("overlay");
    sidebar.style.left="-250px"
    overlay.style.display="none"
}
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    const menubtn = document.getElementById('menu-btn');
    
    menubtn.addEventListener('click', (event) => {
        event.stopPropagation();
        openNav();
    });
    document.addEventListener('click', (event) => {
        if (event.target !== sidebar && !sidebar.contains(event.target)) {
            closeNav();
        }
    });
});

// dropdown in toolbar
document.addEventListener("DOMContentLoaded", function() {
    var dropdown = document.getElementById("profile-dropdown-menu-content");
    var profile_container = document.querySelector(".profile-container");
    profile_container.addEventListener("click", function(event) {
      event.stopPropagation(); 
      if (dropdown.style.display==="block") {
        dropdown.style.display = "none";
      }
      else {
        dropdown.style.display = "block"; 
      }
    });
      window.addEventListener("click", function(event) {
      if (!dropdown.contains(event.target) && !profile_container.contains(event.target)) {
        dropdown.style.display = "none"; 
      }
    });
  });
  document.addEventListener("DOMContentLoaded", function() {
    var dropdown = document.getElementById("class-dropdown-menu-content");
    var class_container = document.querySelector(".class-container");
    class_container.addEventListener("click", function(event) {
      event.stopPropagation(); 
      if (dropdown.style.display==="block") {
        dropdown.style.display = "none";
      }
      else {
        dropdown.style.display = "block"; 
      }
    });
      window.addEventListener("click", function(event) {
      if (!dropdown.contains(event.target) && !class_container.contains(event.target)) {
        dropdown.style.display = "none"; 
      }
    });
  });
  function selectItem(element) {
    var div_element = document.getElementById("class-dropdown-menu-content")
    for(let ele of div_element.children) {
      ele.style.backgroundColor="#fff"
    }
    element.style.backgroundColor = "#594bda20"; 
    var selectedItem = element.textContent;
    document.getElementById('class-dropdown-trigger').textContent = selectedItem;
    div_element.style.display="none"
    for(let ele of div_element.children) {
      if(ele!=element){
        ele.addEventListener('mouseenter', function() {
          ele.style.backgroundColor = '#594bda20'; 
        });
        ele.addEventListener('mouseleave', function() {
          ele.style.backgroundColor = '#fff'; 
        });
      } 
    }
  }