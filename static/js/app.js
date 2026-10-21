'use strict';
document.querySelectorAll('.password-toggle').forEach(b=>b.addEventListener('click',()=>{const i=b.parentElement.querySelector('input'),show=i.type==='password';i.type=show?'text':'password';b.textContent=show?'Hide':'Show';b.setAttribute('aria-pressed',String(show));b.setAttribute('aria-label',show?'Hide password':'Show password');}));
const menu=document.querySelector('.menu-toggle'),sidebar=document.getElementById('sidebar');
if(menu&&sidebar){menu.addEventListener('click',()=>{menu.setAttribute('aria-expanded',String(sidebar.classList.toggle('open')));});document.addEventListener('keydown',e=>{if(e.key==='Escape'){sidebar.classList.remove('open');menu.setAttribute('aria-expanded','false');}});document.addEventListener('click',e=>{if(!sidebar.contains(e.target)&&!menu.contains(e.target)){sidebar.classList.remove('open');menu.setAttribute('aria-expanded','false');}});}
document.querySelectorAll('.sidebar nav a').forEach(a=>{if(a.pathname===location.pathname){a.classList.add('active');a.setAttribute('aria-current','page');}});
document.querySelectorAll('.filter-tabs a').forEach(a=>{if(a.search===location.search){a.classList.add('active');a.setAttribute('aria-current','page');}});
document.querySelectorAll('[data-confirm]').forEach(f=>f.addEventListener('submit',e=>{if(!window.confirm(f.dataset.confirm))e.preventDefault();}));
document.querySelectorAll('.print-button').forEach(b=>b.addEventListener('click',()=>window.print()));
if(document.querySelector('details .errorlist'))document.querySelector('details').open=true;
