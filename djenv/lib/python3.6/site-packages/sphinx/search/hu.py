# -*- coding: utf-8 -*-
"""
    sphinx.search.hu
    ~~~~~~~~~~~~~~~~

    Hungarian search language: includes the JS Hungarian stemmer.

    :copyright: Copyright 2007-2013 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from sphinx.search import SearchLanguage, parse_stop_word

import snowballstemmer

if False:
    # For type annotation
    from typing import Any  # NOQA


hungarian_stopwords = parse_stop_word(u'''
| source: http://snowball.tartarus.org/algorithms/hungarian/stop.txt
| prepared by Anna Tordai
a
ahogy
ahol
aki
akik
akkor
alatt
által
általában
amely
amelyek
amelyekben
amelyeket
amelyet
amelynek
ami
amit
amolyan
amíg
amikor
át
abban
ahhoz
annak
arra
arról
az
azok
azon
azt
azzal
azért
aztán
azután
azonban
bár
be
belül
benne
cikk
cikkek
cikkeket
csak
de
e
eddig
egész
egy
egyes
egyetlen
egyéb
egyik
egyre
ekkor
el
elég
ellen
elő
először
előtt
első
én
éppen
ebben
ehhez
emilyen
ennek
erre
ez
ezt
ezek
ezen
ezzel
ezért
és
fel
felé
hanem
hiszen
hogy
hogyan
igen
így
illetve
ill.
ill
ilyen
ilyenkor
ison
ismét
itt
jó
jól
jobban
kell
kellett
keresztül
keressünk
ki
kívül
között
közül
legalább
lehet
lehetett
legyen
lenne
lenni
lesz
lett
maga
magát
majd
majd
már
más
másik
meg
még
mellett
mert
mely
melyek
mi
mit
míg
miért
milyen
mikor
minden
mindent
mindenki
mindig
mint
mintha
mivel
most
nagy
nagyobb
nagyon
ne
néha
nekem
neki
nem
néhány
nélkül
nincs
olyan
ott
össze
ő
ők
őket
pedig
persze
rá
s
saját
sem
semmi
sok
sokat
sokkal
számára
szemben
szerint
szinte
talán
tehát
teljes
tovább
továbbá
több
úgy
ugyanis
új
újabb
újra
után
utána
utolsó
vagy
vagyis
valaki
valami
valamint
való
vagyok
van
vannak
volt
voltam
voltak
voltunk
vissza
vele
viszont
volna
''')

js_stemmer = u"""

var JSX={};(function(h){function j(b,e){var a=function(){};a.prototype=e.prototype;var c=new a;for(var d in b){b[d].prototype=c}}function P(c,b){for(var a in b.prototype)if(b.prototype.hasOwnProperty(a))c.prototype[a]=b.prototype[a]}function e(a,b,d){function c(a,b,c){delete a[b];a[b]=c;return c}Object.defineProperty(a,b,{get:function(){return c(a,b,d())},set:function(d){c(a,b,d)},enumerable:true,configurable:true})}function O(a,b,c){return a[b]=a[b]/c|0}var u=parseInt;var v=parseFloat;function N(a){return a!==a}var x=isFinite;var y=encodeURIComponent;var z=decodeURIComponent;var B=encodeURI;var C=decodeURI;var E=Object.prototype.toString;var F=Object.prototype.hasOwnProperty;function i(){}h.require=function(b){var a=q[b];return a!==undefined?a:null};h.profilerIsRunning=function(){return i.getResults!=null};h.getProfileResults=function(){return(i.getResults||function(){return{}})()};h.postProfileResults=function(a,b){if(i.postResults==null)throw new Error('profiler has not been turned on');return i.postResults(a,b)};h.resetProfileResults=function(){if(i.resetResults==null)throw new Error('profiler has not been turned on');return i.resetResults()};h.DEBUG=false;function r(){};j([r],Error);function a(a,b,c){this.F=a.length;this.K=a;this.L=b;this.I=c;this.H=null;this.P=null};j([a],Object);function n(){};j([n],Object);function f(){var a;var b;var c;this.G={};a=this.D='';b=this._=0;c=this.A=a.length;this.E=0;this.B=b;this.C=c};j([f],n);function s(a,b){a.D=b.D;a._=b._;a.A=b.A;a.E=b.E;a.B=b.B;a.C=b.C};function k(b,d,c,e){var a;if(b._>=b.A){return false}a=b.D.charCodeAt(b._);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._++;return true};function l(a,d,c,e){var b;if(a._>=a.A){return false}b=a.D.charCodeAt(a._);if(b>e||b<c){a._++;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._++;return true}return false};function o(f,m,p){var b;var d;var e;var n;var g;var k;var l;var i;var h;var c;var a;var j;var o;b=0;d=p;e=f._;n=f.A;g=0;k=0;l=false;while(true){i=b+(d-b>>>1);h=0;c=g<k?g:k;a=m[i];for(j=c;j<a.F;j++){if(e+c===n){h=-1;break}h=f.D.charCodeAt(e+c)-a.K.charCodeAt(j);if(h!==0){break}c++}if(h<0){d=i;k=c}else{b=i;g=c}if(d-b<=1){if(b>0){break}if(d===b){break}if(l){break}l=true}}while(true){a=m[b];if(g>=a.F){f._=e+a.F|0;if(a.H==null){return a.I}o=a.H(a.P);f._=e+a.F|0;if(o){return a.I}}b=a.L;if(b<0){return 0}}return-1};function d(d,m,p){var b;var g;var e;var n;var f;var k;var l;var i;var h;var c;var a;var j;var o;b=0;g=p;e=d._;n=d.E;f=0;k=0;l=false;while(true){i=b+(g-b>>1);h=0;c=f<k?f:k;a=m[i];for(j=a.F-1-c;j>=0;j--){if(e-c===n){h=-1;break}h=d.D.charCodeAt(e-1-c)-a.K.charCodeAt(j);if(h!==0){break}c++}if(h<0){g=i;k=c}else{b=i;f=c}if(g-b<=1){if(b>0){break}if(g===b){break}if(l){break}l=true}}while(true){a=m[b];if(f>=a.F){d._=e-a.F|0;if(a.H==null){return a.I}o=a.H(d);d._=e-a.F|0;if(o){return a.I}}b=a.L;if(b<0){return 0}}return-1};function A(a,b,d,e){var c;c=e.length-(d-b);a.D=a.D.slice(0,b)+e+a.D.slice(d);a.A+=c|0;if(a._>=d){a._+=c|0}else if(a._>b){a._=b}return c|0};function b(a,f){var b;var c;var d;var e;b=false;if((c=a.B)<0||c>(d=a.C)||d>(e=a.A)||e>a.D.length?false:true){A(a,a.B,a.C,f);b=true}return b};f.prototype.J=function(){return false};f.prototype.e=function(b){var a;var c;var d;var e;a=this.G['.'+b];if(a==null){c=this.D=b;d=this._=0;e=this.A=c.length;this.E=0;this.B=d;this.C=e;this.J();a=this.D;this.G['.'+b]=a}return a};f.prototype.stemWord=f.prototype.e;f.prototype.f=function(e){var d;var b;var c;var a;var f;var g;var h;d=[];for(b=0;b<e.length;b++){c=e[b];a=this.G['.'+c];if(a==null){f=this.D=c;g=this._=0;h=this.A=f.length;this.E=0;this.B=g;this.C=h;this.J();a=this.D;this.G['.'+c]=a}d.push(a)}return d};f.prototype.stemWords=f.prototype.f;function c(){f.call(this);this.I_p1=0};j([c],f);c.prototype.M=function(a){this.I_p1=a.I_p1;s(this,a)};c.prototype.copy_from=c.prototype.M;c.prototype.X=function(){var m;var b;var j;var d;var e;var a;var f;var g;var h;var n;var i;this.I_p1=this.A;d=true;b:while(d===true){d=false;m=this._;e=true;a:while(e===true){e=false;if(!k(this,c.g_v,97,252)){break a}c:while(true){b=this._;a=true;d:while(a===true){a=false;if(!l(this,c.g_v,97,252)){break d}this._=b;break c}n=this._=b;if(n>=this.A){break a}this._++}f=true;c:while(f===true){f=false;j=this._;g=true;d:while(g===true){g=false;if(o(this,c.a_0,8)===0){break d}break c}i=this._=j;if(i>=this.A){break a}this._++}this.I_p1=this._;break b}this._=m;if(!l(this,c.g_v,97,252)){return false}a:while(true){h=true;c:while(h===true){h=false;if(!k(this,c.g_v,97,252)){break c}break a}if(this._>=this.A){return false}this._++}this.I_p1=this._}return true};c.prototype.r_mark_regions=c.prototype.X;function D(a){var j;var d;var n;var e;var b;var f;var g;var h;var i;var p;var m;a.I_p1=a.A;e=true;b:while(e===true){e=false;j=a._;b=true;a:while(b===true){b=false;if(!k(a,c.g_v,97,252)){break a}c:while(true){d=a._;f=true;d:while(f===true){f=false;if(!l(a,c.g_v,97,252)){break d}a._=d;break c}p=a._=d;if(p>=a.A){break a}a._++}g=true;c:while(g===true){g=false;n=a._;h=true;d:while(h===true){h=false;if(o(a,c.a_0,8)===0){break d}break c}m=a._=n;if(m>=a.A){break a}a._++}a.I_p1=a._;break b}a._=j;if(!l(a,c.g_v,97,252)){return false}a:while(true){i=true;c:while(i===true){i=false;if(!k(a,c.g_v,97,252)){break c}break a}if(a._>=a.A){return false}a._++}a.I_p1=a._}return true};c.prototype.Q=function(){return!(this.I_p1<=this._)?false:true};c.prototype.r_R1=c.prototype.Q;c.prototype.d=function(){var a;var e;this.C=this._;a=d(this,c.a_1,2);if(a===0){return false}this.B=e=this._;if(!(!(this.I_p1<=e)?false:true)){return false}switch(a){case 0:return false;case 1:if(!b(this,'a')){return false}break;case 2:if(!b(this,'e')){return false}break}return true};c.prototype.r_v_ending=c.prototype.d;function p(a){var e;var f;a.C=a._;e=d(a,c.a_1,2);if(e===0){return false}a.B=f=a._;if(!(!(a.I_p1<=f)?false:true)){return false}switch(e){case 0:return false;case 1:if(!b(a,'a')){return false}break;case 2:if(!b(a,'e')){return false}break}return true};c.prototype.U=function(){var a;a=this.A-this._;if(d(this,c.a_2,23)===0){return false}this._=this.A-a;return true};c.prototype.r_double=c.prototype.U;function g(a){var b;b=a.A-a._;if(d(a,c.a_2,23)===0){return false}a._=a.A-b;return true};c.prototype.c=function(){var a;var c;var d;if(this._<=this.E){return false}this._--;this.C=c=this._;a=c-1|0;if(this.E>a||a>this.A){return false}d=this._=a;this.B=d;return!b(this,'')?false:true};c.prototype.r_undouble=c.prototype.c;function m(a){var c;var d;var e;if(a._<=a.E){return false}a._--;a.C=d=a._;c=d-1|0;if(a.E>c||c>a.A){return false}e=a._=c;a.B=e;return!b(a,'')?false:true};c.prototype.W=function(){var a;var e;this.C=this._;a=d(this,c.a_3,2);if(a===0){return false}this.B=e=this._;if(!(!(this.I_p1<=e)?false:true)){return false}switch(a){case 0:return false;case 1:if(!g(this)){return false}break;case 2:if(!g(this)){return false}break}return!b(this,'')?false:!m(this)?false:true};c.prototype.r_instrum=c.prototype.W;function H(a){var e;var f;a.C=a._;e=d(a,c.a_3,2);if(e===0){return false}a.B=f=a._;if(!(!(a.I_p1<=f)?false:true)){return false}switch(e){case 0:return false;case 1:if(!g(a)){return false}break;case 2:if(!g(a)){return false}break}return!b(a,'')?false:!m(a)?false:true};c.prototype.R=function(){var a;this.C=this._;if(d(this,c.a_4,44)===0){return false}this.B=a=this._;return!(!(this.I_p1<=a)?false:true)?false:!b(this,'')?false:!p(this)?false:true};c.prototype.r_case=c.prototype.R;function I(a){var e;a.C=a._;if(d(a,c.a_4,44)===0){return false}a.B=e=a._;return!(!(a.I_p1<=e)?false:true)?false:!b(a,'')?false:!p(a)?false:true};c.prototype.T=function(){var a;var e;this.C=this._;a=d(this,c.a_5,3);if(a===0){return false}this.B=e=this._;if(!(!(this.I_p1<=e)?false:true)){return false}switch(a){case 0:return false;case 1:if(!b(this,'e')){return false}break;case 2:if(!b(this,'a')){return false}break;case 3:if(!b(this,'a')){return false}break}return true};c.prototype.r_case_special=c.prototype.T;function J(a){var e;var f;a.C=a._;e=d(a,c.a_5,3);if(e===0){return false}a.B=f=a._;if(!(!(a.I_p1<=f)?false:true)){return false}switch(e){case 0:return false;case 1:if(!b(a,'e')){return false}break;case 2:if(!b(a,'a')){return false}break;case 3:if(!b(a,'a')){return false}break}return true};c.prototype.S=function(){var a;var e;this.C=this._;a=d(this,c.a_6,6);if(a===0){return false}this.B=e=this._;if(!(!(this.I_p1<=e)?false:true)){return false}switch(a){case 0:return false;case 1:if(!b(this,'')){return false}break;case 2:if(!b(this,'')){return false}break;case 3:if(!b(this,'a')){return false}break;case 4:if(!b(this,'e')){return false}break}return true};c.prototype.r_case_other=c.prototype.S;function K(a){var e;var f;a.C=a._;e=d(a,c.a_6,6);if(e===0){return false}a.B=f=a._;if(!(!(a.I_p1<=f)?false:true)){return false}switch(e){case 0:return false;case 1:if(!b(a,'')){return false}break;case 2:if(!b(a,'')){return false}break;case 3:if(!b(a,'a')){return false}break;case 4:if(!b(a,'e')){return false}break}return true};c.prototype.V=function(){var a;var e;this.C=this._;a=d(this,c.a_7,2);if(a===0){return false}this.B=e=this._;if(!(!(this.I_p1<=e)?false:true)){return false}switch(a){case 0:return false;case 1:if(!g(this)){return false}break;case 2:if(!g(this)){return false}break}return!b(this,'')?false:!m(this)?false:true};c.prototype.r_factive=c.prototype.V;function L(a){var e;var f;a.C=a._;e=d(a,c.a_7,2);if(e===0){return false}a.B=f=a._;if(!(!(a.I_p1<=f)?false:true)){return false}switch(e){case 0:return false;case 1:if(!g(a)){return false}break;case 2:if(!g(a)){return false}break}return!b(a,'')?false:!m(a)?false:true};c.prototype.a=function(){var a;var e;this.C=this._;a=d(this,c.a_8,7);if(a===0){return false}this.B=e=this._;if(!(!(this.I_p1<=e)?false:true)){return false}switch(a){case 0:return false;case 1:if(!b(this,'a')){return false}break;case 2:if(!b(this,'e')){return false}break;case 3:if(!b(this,'')){return false}break;case 4:if(!b(this,'')){return false}break;case 5:if(!b(this,'')){return false}break;case 6:if(!b(this,'')){return false}break;case 7:if(!b(this,'')){return false}break}return true};c.prototype.r_plural=c.prototype.a;function M(a){var e;var f;a.C=a._;e=d(a,c.a_8,7);if(e===0){return false}a.B=f=a._;if(!(!(a.I_p1<=f)?false:true)){return false}switch(e){case 0:return false;case 1:if(!b(a,'a')){return false}break;case 2:if(!b(a,'e')){return false}break;case 3:if(!b(a,'')){return false}break;case 4:if(!b(a,'')){return false}break;case 5:if(!b(a,'')){return false}break;case 6:if(!b(a,'')){return false}break;case 7:if(!b(a,'')){return false}break}return true};c.prototype.Y=function(){var a;var e;this.C=this._;a=d(this,c.a_9,12);if(a===0){return false}this.B=e=this._;if(!(!(this.I_p1<=e)?false:true)){return false}switch(a){case 0:return false;case 1:if(!b(this,'')){return false}break;case 2:if(!b(this,'e')){return false}break;case 3:if(!b(this,'a')){return false}break;case 4:if(!b(this,'')){return false}break;case 5:if(!b(this,'e')){return false}break;case 6:if(!b(this,'a')){return false}break;case 7:if(!b(this,'')){return false}break;case 8:if(!b(this,'e')){return false}break;case 9:if(!b(this,'')){return false}break}return true};c.prototype.r_owned=c.prototype.Y;function w(a){var e;var f;a.C=a._;e=d(a,c.a_9,12);if(e===0){return false}a.B=f=a._;if(!(!(a.I_p1<=f)?false:true)){return false}switch(e){case 0:return false;case 1:if(!b(a,'')){return false}break;case 2:if(!b(a,'e')){return false}break;case 3:if(!b(a,'a')){return false}break;case 4:if(!b(a,'')){return false}break;case 5:if(!b(a,'e')){return false}break;case 6:if(!b(a,'a')){return false}break;case 7:if(!b(a,'')){return false}break;case 8:if(!b(a,'e')){return false}break;case 9:if(!b(a,'')){return false}break}return true};c.prototype.b=function(){var a;var e;this.C=this._;a=d(this,c.a_10,31);if(a===0){return false}this.B=e=this._;if(!(!(this.I_p1<=e)?false:true)){return false}switch(a){case 0:return false;case 1:if(!b(this,'')){return false}break;case 2:if(!b(this,'a')){return false}break;case 3:if(!b(this,'e')){return false}break;case 4:if(!b(this,'')){return false}break;case 5:if(!b(this,'a')){return false}break;case 6:if(!b(this,'e')){return false}break;case 7:if(!b(this,'')){return false}break;case 8:if(!b(this,'')){return false}break;case 9:if(!b(this,'')){return false}break;case 10:if(!b(this,'a')){return false}break;case 11:if(!b(this,'e')){return false}break;case 12:if(!b(this,'')){return false}break;case 13:if(!b(this,'')){return false}break;case 14:if(!b(this,'a')){return false}break;case 15:if(!b(this,'e')){return false}break;case 16:if(!b(this,'')){return false}break;case 17:if(!b(this,'')){return false}break;case 18:if(!b(this,'')){return false}break;case 19:if(!b(this,'a')){return false}break;case 20:if(!b(this,'e')){return false}break}return true};c.prototype.r_sing_owner=c.prototype.b;function t(a){var e;var f;a.C=a._;e=d(a,c.a_10,31);if(e===0){return false}a.B=f=a._;if(!(!(a.I_p1<=f)?false:true)){return false}switch(e){case 0:return false;case 1:if(!b(a,'')){return false}break;case 2:if(!b(a,'a')){return false}break;case 3:if(!b(a,'e')){return false}break;case 4:if(!b(a,'')){return false}break;case 5:if(!b(a,'a')){return false}break;case 6:if(!b(a,'e')){return false}break;case 7:if(!b(a,'')){return false}break;case 8:if(!b(a,'')){return false}break;case 9:if(!b(a,'')){return false}break;case 10:if(!b(a,'a')){return false}break;case 11:if(!b(a,'e')){return false}break;case 12:if(!b(a,'')){return false}break;case 13:if(!b(a,'')){return false}break;case 14:if(!b(a,'a')){return false}break;case 15:if(!b(a,'e')){return false}break;case 16:if(!b(a,'')){return false}break;case 17:if(!b(a,'')){return false}break;case 18:if(!b(a,'')){return false}break;case 19:if(!b(a,'a')){return false}break;case 20:if(!b(a,'e')){return false}break}return true};c.prototype.Z=function(){var a;var e;this.C=this._;a=d(this,c.a_11,42);if(a===0){return false}this.B=e=this._;if(!(!(this.I_p1<=e)?false:true)){return false}switch(a){case 0:return false;case 1:if(!b(this,'')){return false}break;case 2:if(!b(this,'a')){return false}break;case 3:if(!b(this,'e')){return false}break;case 4:if(!b(this,'')){return false}break;case 5:if(!b(this,'')){return false}break;case 6:if(!b(this,'')){return false}break;case 7:if(!b(this,'a')){return false}break;case 8:if(!b(this,'e')){return false}break;case 9:if(!b(this,'')){return false}break;case 10:if(!b(this,'')){return false}break;case 11:if(!b(this,'')){return false}break;case 12:if(!b(this,'a')){return false}break;case 13:if(!b(this,'e')){return false}break;case 14:if(!b(this,'')){return false}break;case 15:if(!b(this,'')){return false}break;case 16:if(!b(this,'')){return false}break;case 17:if(!b(this,'')){return false}break;case 18:if(!b(this,'a')){return false}break;case 19:if(!b(this,'e')){return false}break;case 20:if(!b(this,'')){return false}break;case 21:if(!b(this,'')){return false}break;case 22:if(!b(this,'a')){return false}break;case 23:if(!b(this,'e')){return false}break;case 24:if(!b(this,'')){return false}break;case 25:if(!b(this,'')){return false}break;case 26:if(!b(this,'')){return false}break;case 27:if(!b(this,'a')){return false}break;case 28:if(!b(this,'e')){return false}break;case 29:if(!b(this,'')){return false}break}return true};c.prototype.r_plur_owner=c.prototype.Z;function G(a){var e;var f;a.C=a._;e=d(a,c.a_11,42);if(e===0){return false}a.B=f=a._;if(!(!(a.I_p1<=f)?false:true)){return false}switch(e){case 0:return false;case 1:if(!b(a,'')){return false}break;case 2:if(!b(a,'a')){return false}break;case 3:if(!b(a,'e')){return false}break;case 4:if(!b(a,'')){return false}break;case 5:if(!b(a,'')){return false}break;case 6:if(!b(a,'')){return false}break;case 7:if(!b(a,'a')){return false}break;case 8:if(!b(a,'e')){return false}break;case 9:if(!b(a,'')){return false}break;case 10:if(!b(a,'')){return false}break;case 11:if(!b(a,'')){return false}break;case 12:if(!b(a,'a')){return false}break;case 13:if(!b(a,'e')){return false}break;case 14:if(!b(a,'')){return false}break;case 15:if(!b(a,'')){return false}break;case 16:if(!b(a,'')){return false}break;case 17:if(!b(a,'')){return false}break;case 18:if(!b(a,'a')){return false}break;case 19:if(!b(a,'e')){return false}break;case 20:if(!b(a,'')){return false}break;case 21:if(!b(a,'')){return false}break;case 22:if(!b(a,'a')){return false}break;case 23:if(!b(a,'e')){return false}break;case 24:if(!b(a,'')){return false}break;case 25:if(!b(a,'')){return false}break;case 26:if(!b(a,'')){return false}break;case 27:if(!b(a,'a')){return false}break;case 28:if(!b(a,'e')){return false}break;case 29:if(!b(a,'')){return false}break}return true};c.prototype.J=function(){var s;var l;var m;var n;var o;var p;var q;var r;var u;var b;var c;var d;var e;var f;var g;var h;var i;var a;var j;var v;var x;var y;var z;var A;var B;var C;var E;var F;var N;var O;var P;var Q;var R;var S;var T;var k;s=this._;b=true;a:while(b===true){b=false;if(!D(this)){break a}}v=this._=s;this.E=v;y=this._=x=this.A;l=x-y;c=true;a:while(c===true){c=false;if(!H(this)){break a}}A=this._=(z=this.A)-l;m=z-A;d=true;a:while(d===true){d=false;if(!I(this)){break a}}C=this._=(B=this.A)-m;n=B-C;e=true;a:while(e===true){e=false;if(!J(this)){break a}}F=this._=(E=this.A)-n;o=E-F;f=true;a:while(f===true){f=false;if(!K(this)){break a}}O=this._=(N=this.A)-o;p=N-O;g=true;a:while(g===true){g=false;if(!L(this)){break a}}Q=this._=(P=this.A)-p;q=P-Q;h=true;a:while(h===true){h=false;if(!w(this)){break a}}S=this._=(R=this.A)-q;r=R-S;i=true;a:while(i===true){i=false;if(!t(this)){break a}}k=this._=(T=this.A)-r;u=T-k;a=true;a:while(a===true){a=false;if(!G(this)){break a}}this._=this.A-u;j=true;a:while(j===true){j=false;if(!M(this)){break a}}this._=this.E;return true};c.prototype.stem=c.prototype.J;c.prototype.N=function(a){return a instanceof c};c.prototype.equals=c.prototype.N;c.prototype.O=function(){var c;var a;var b;var d;c='HungarianStemmer';a=0;for(b=0;b<c.length;b++){d=c.charCodeAt(b);a=(a<<5)-a+d;a=a&a}return a|0};c.prototype.hashCode=c.prototype.O;c.serialVersionUID=1;e(c,'methodObject',function(){return new c});e(c,'a_0',function(){return[new a('cs',-1,-1),new a('dzs',-1,-1),new a('gy',-1,-1),new a('ly',-1,-1),new a('ny',-1,-1),new a('sz',-1,-1),new a('ty',-1,-1),new a('zs',-1,-1)]});e(c,'a_1',function(){return[new a('á',-1,1),new a('é',-1,2)]});e(c,'a_2',function(){return[new a('bb',-1,-1),new a('cc',-1,-1),new a('dd',-1,-1),new a('ff',-1,-1),new a('gg',-1,-1),new a('jj',-1,-1),new a('kk',-1,-1),new a('ll',-1,-1),new a('mm',-1,-1),new a('nn',-1,-1),new a('pp',-1,-1),new a('rr',-1,-1),new a('ccs',-1,-1),new a('ss',-1,-1),new a('zzs',-1,-1),new a('tt',-1,-1),new a('vv',-1,-1),new a('ggy',-1,-1),new a('lly',-1,-1),new a('nny',-1,-1),new a('tty',-1,-1),new a('ssz',-1,-1),new a('zz',-1,-1)]});e(c,'a_3',function(){return[new a('al',-1,1),new a('el',-1,2)]});e(c,'a_4',function(){return[new a('ba',-1,-1),new a('ra',-1,-1),new a('be',-1,-1),new a('re',-1,-1),new a('ig',-1,-1),new a('nak',-1,-1),new a('nek',-1,-1),new a('val',-1,-1),new a('vel',-1,-1),new a('ul',-1,-1),new a('nál',-1,-1),new a('nél',-1,-1),new a('ból',-1,-1),new a('ról',-1,-1),new a('tól',-1,-1),new a('bõl',-1,-1),new a('rõl',-1,-1),new a('tõl',-1,-1),new a('ül',-1,-1),new a('n',-1,-1),new a('an',19,-1),new a('ban',20,-1),new a('en',19,-1),new a('ben',22,-1),new a('képpen',22,-1),new a('on',19,-1),new a('ön',19,-1),new a('képp',-1,-1),new a('kor',-1,-1),new a('t',-1,-1),new a('at',29,-1),new a('et',29,-1),new a('ként',29,-1),new a('anként',32,-1),new a('enként',32,-1),new a('onként',32,-1),new a('ot',29,-1),new a('ért',29,-1),new a('öt',29,-1),new a('hez',-1,-1),new a('hoz',-1,-1),new a('höz',-1,-1),new a('vá',-1,-1),new a('vé',-1,-1)]});e(c,'a_5',function(){return[new a('án',-1,2),new a('én',-1,1),new a('ánként',-1,3)]});e(c,'a_6',function(){return[new a('stul',-1,2),new a('astul',0,1),new a('ástul',0,3),new a('stül',-1,2),new a('estül',3,1),new a('éstül',3,4)]});e(c,'a_7',function(){return[new a('á',-1,1),new a('é',-1,2)]});e(c,'a_8',function(){return[new a('k',-1,7),new a('ak',0,4),new a('ek',0,6),new a('ok',0,5),new a('ák',0,1),new a('ék',0,2),new a('ök',0,3)]});e(c,'a_9',function(){return[new a('éi',-1,7),new a('áéi',0,6),new a('ééi',0,5),new a('é',-1,9),new a('ké',3,4),new a('aké',4,1),new a('eké',4,1),new a('oké',4,1),new a('áké',4,3),new a('éké',4,2),new a('öké',4,1),new a('éé',3,8)]});e(c,'a_10',function(){return[new a('a',-1,18),new a('ja',0,17),new a('d',-1,16),new a('ad',2,13),new a('ed',2,13),new a('od',2,13),new a('ád',2,14),new a('éd',2,15),new a('öd',2,13),new a('e',-1,18),new a('je',9,17),new a('nk',-1,4),new a('unk',11,1),new a('ánk',11,2),new a('énk',11,3),new a('ünk',11,1),new a('uk',-1,8),new a('juk',16,7),new a('ájuk',17,5),new a('ük',-1,8),new a('jük',19,7),new a('éjük',20,6),new a('m',-1,12),new a('am',22,9),new a('em',22,9),new a('om',22,9),new a('ám',22,10),new a('ém',22,11),new a('o',-1,18),new a('á',-1,19),new a('é',-1,20)]});e(c,'a_11',function(){return[new a('id',-1,10),new a('aid',0,9),new a('jaid',1,6),new a('eid',0,9),new a('jeid',3,6),new a('áid',0,7),new a('éid',0,8),new a('i',-1,15),new a('ai',7,14),new a('jai',8,11),new a('ei',7,14),new a('jei',10,11),new a('ái',7,12),new a('éi',7,13),new a('itek',-1,24),new a('eitek',14,21),new a('jeitek',15,20),new a('éitek',14,23),new a('ik',-1,29),new a('aik',18,26),new a('jaik',19,25),new a('eik',18,26),new a('jeik',21,25),new a('áik',18,27),new a('éik',18,28),new a('ink',-1,20),new a('aink',25,17),new a('jaink',26,16),new a('eink',25,17),new a('jeink',28,16),new a('áink',25,18),new a('éink',25,19),new a('aitok',-1,21),new a('jaitok',32,20),new a('áitok',-1,22),new a('im',-1,5),new a('aim',35,4),new a('jaim',36,1),new a('eim',35,4),new a('jeim',38,1),new a('áim',35,2),new a('éim',35,3)]});e(c,'g_v',function(){return[17,65,16,0,0,0,0,0,0,0,0,0,0,0,0,0,1,17,52,14]});var q={'src/stemmer.jsx':{Stemmer:n},'src/hungarian-stemmer.jsx':{HungarianStemmer:c}}}(JSX))
var Stemmer = JSX.require("src/hungarian-stemmer.jsx").HungarianStemmer;
"""


class SearchHungarian(SearchLanguage):
    lang = 'hu'
    language_name = 'Hungarian'
    js_stemmer_rawcode = 'hungarian-stemmer.js'
    js_stemmer_code = js_stemmer
    stopwords = hungarian_stopwords

    def init(self, options):
        # type: (Any) -> None
        self.stemmer = snowballstemmer.stemmer('hungarian')

    def stem(self, word):
        # type: (unicode) -> unicode
        return self.stemmer.stemWord(word.lower())
