'use strict';
document.querySelectorAll('.password-toggle').forEach(b=>b.addEventListener('click',()=>{const i=b.parentElement.querySelector('input'),show=i.type==='password';i.type=show?'text':'password';b.textContent=show?'Hide':'Show';b.setAttribute('aria-pressed',String(show));b.setAttribute('aria-label',show?'Hide password':'Show password');}));
const menu=document.querySelector('.menu-toggle'),sidebar=document.getElementById('sidebar');
if(menu&&sidebar){menu.addEventListener('click',()=>{menu.setAttribute('aria-expanded',String(sidebar.classList.toggle('open')));});document.addEventListener('keydown',e=>{if(e.key==='Escape'){sidebar.classList.remove('open');menu.setAttribute('aria-expanded','false');}});document.addEventListener('click',e=>{if(!sidebar.contains(e.target)&&!menu.contains(e.target)){sidebar.classList.remove('open');menu.setAttribute('aria-expanded','false');}});}
document.querySelectorAll('.sidebar nav a').forEach(a=>{if(a.pathname===location.pathname){a.classList.add('active');a.setAttribute('aria-current','page');}});
document.querySelectorAll('.filter-tabs a').forEach(a=>{if(a.search===location.search){a.classList.add('active');a.setAttribute('aria-current','page');}});
document.querySelectorAll('[data-confirm]').forEach(f=>f.addEventListener('submit',e=>{if(!window.confirm(f.dataset.confirm))e.preventDefault();}));
document.querySelectorAll('.print-button').forEach(b=>b.addEventListener('click',()=>window.print()));
if(document.querySelector('details .errorlist'))document.querySelector('details').open=true;

// A collapsible public menu keeps navigation readable on small screens.
const publicMenu=document.querySelector('.public-menu'),publicNav=document.querySelector('.public-nav');
if(publicMenu&&publicNav){publicMenu.addEventListener('click',()=>{publicMenu.setAttribute('aria-expanded',String(publicNav.classList.toggle('open')));});document.addEventListener('keydown',e=>{if(e.key==='Escape'){publicNav.classList.remove('open');publicMenu.setAttribute('aria-expanded','false');publicMenu.focus();}});}
document.querySelectorAll('.public-nav a').forEach(a=>{if(a.pathname===location.pathname)a.setAttribute('aria-current','page');});
// Keep submitted button names/values intact. Block repeated POSTs without changing payloads.
document.querySelectorAll('form[method="post"]').forEach(form=>{form.addEventListener('submit',event=>{if(event.defaultPrevented)return;if(form.dataset.submitting){event.preventDefault();return;}form.dataset.submitting='true';form.setAttribute('aria-busy','true');const button=event.submitter;if(button){button.setAttribute('aria-disabled','true');const spinner=document.createElement('span');spinner.className='loading-mark';spinner.setAttribute('aria-hidden','true');button.prepend(spinner);}});});
window.addEventListener('pageshow',()=>{document.querySelectorAll('form[data-submitting]').forEach(form=>{delete form.dataset.submitting;form.removeAttribute('aria-busy');form.querySelectorAll('[aria-disabled="true"]').forEach(button=>button.removeAttribute('aria-disabled'));form.querySelectorAll('.loading-mark').forEach(spinner=>spinner.remove());});});
// Keyboard users can reach a field error immediately after server validation.
const invalidField=document.querySelector('[aria-invalid="true"]');if(invalidField){const details=invalidField.closest('details');if(details)details.open=true;invalidField.focus();}

// Off-canvas links must leave the tab order while the mobile drawer is closed.
if(sidebar&&menu){const narrow=window.matchMedia('(max-width:820px)');const syncDrawer=()=>{const open=sidebar.classList.contains('open');sidebar.inert=narrow.matches&&!open;document.body.classList.toggle('navigation-open',narrow.matches&&open);};syncDrawer();new MutationObserver(syncDrawer).observe(sidebar,{attributes:true,attributeFilter:['class']});narrow.addEventListener('change',syncDrawer);menu.addEventListener('click',()=>{syncDrawer();if(sidebar.classList.contains('open'))sidebar.querySelector('nav a')?.focus();});document.addEventListener('keydown',event=>{if(event.key==='Escape'&&narrow.matches&&sidebar.classList.contains('open')){sidebar.classList.remove('open');menu.setAttribute('aria-expanded','false');syncDrawer();menu.focus();}},true);}

// Booking feedback reflects a real selected radio; reservation remains server-side.
document.querySelectorAll('.booking-form input[name="slot"]').forEach(input=>input.addEventListener('change',()=>{const summary=document.querySelector('.booking-selection');if(summary){summary.querySelector('strong').textContent=input.dataset.label;summary.querySelector('p').textContent='Selected time. Complete your visit details to request this appointment.';}}));

document.querySelectorAll('.print-page').forEach(button=>button.addEventListener('click',()=>window.print()));
