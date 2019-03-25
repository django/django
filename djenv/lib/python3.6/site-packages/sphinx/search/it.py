# -*- coding: utf-8 -*-
"""
    sphinx.search.it
    ~~~~~~~~~~~~~~~~

    Italian search language: includes the JS Italian stemmer.

    :copyright: Copyright 2007-2013 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from sphinx.search import SearchLanguage, parse_stop_word

import snowballstemmer

if False:
    # For type annotation
    from typing import Any  # NOQA


italian_stopwords = parse_stop_word(u'''
| source: http://snowball.tartarus.org/algorithms/italian/stop.txt
ad             |  a (to) before vowel
al             |  a + il
allo           |  a + lo
ai             |  a + i
agli           |  a + gli
all            |  a + l'
agl            |  a + gl'
alla           |  a + la
alle           |  a + le
con            |  with
col            |  con + il
coi            |  con + i (forms collo, cogli etc are now very rare)
da             |  from
dal            |  da + il
dallo          |  da + lo
dai            |  da + i
dagli          |  da + gli
dall           |  da + l'
dagl           |  da + gll'
dalla          |  da + la
dalle          |  da + le
di             |  of
del            |  di + il
dello          |  di + lo
dei            |  di + i
degli          |  di + gli
dell           |  di + l'
degl           |  di + gl'
della          |  di + la
delle          |  di + le
in             |  in
nel            |  in + el
nello          |  in + lo
nei            |  in + i
negli          |  in + gli
nell           |  in + l'
negl           |  in + gl'
nella          |  in + la
nelle          |  in + le
su             |  on
sul            |  su + il
sullo          |  su + lo
sui            |  su + i
sugli          |  su + gli
sull           |  su + l'
sugl           |  su + gl'
sulla          |  su + la
sulle          |  su + le
per            |  through, by
tra            |  among
contro         |  against
io             |  I
tu             |  thou
lui            |  he
lei            |  she
noi            |  we
voi            |  you
loro           |  they
mio            |  my
mia            |
miei           |
mie            |
tuo            |
tua            |
tuoi           |  thy
tue            |
suo            |
sua            |
suoi           |  his, her
sue            |
nostro         |  our
nostra         |
nostri         |
nostre         |
vostro         |  your
vostra         |
vostri         |
vostre         |
mi             |  me
ti             |  thee
ci             |  us, there
vi             |  you, there
lo             |  him, the
la             |  her, the
li             |  them
le             |  them, the
gli            |  to him, the
ne             |  from there etc
il             |  the
un             |  a
uno            |  a
una            |  a
ma             |  but
ed             |  and
se             |  if
perché         |  why, because
anche          |  also
come           |  how
dov            |  where (as dov')
dove           |  where
che            |  who, that
chi            |  who
cui            |  whom
non            |  not
più            |  more
quale          |  who, that
quanto         |  how much
quanti         |
quanta         |
quante         |
quello         |  that
quelli         |
quella         |
quelle         |
questo         |  this
questi         |
questa         |
queste         |
si             |  yes
tutto          |  all
tutti          |  all

               |  single letter forms:

a              |  at
c              |  as c' for ce or ci
e              |  and
i              |  the
l              |  as l'
o              |  or

               | forms of avere, to have (not including the infinitive):

ho
hai
ha
abbiamo
avete
hanno
abbia
abbiate
abbiano
avrò
avrai
avrà
avremo
avrete
avranno
avrei
avresti
avrebbe
avremmo
avreste
avrebbero
avevo
avevi
aveva
avevamo
avevate
avevano
ebbi
avesti
ebbe
avemmo
aveste
ebbero
avessi
avesse
avessimo
avessero
avendo
avuto
avuta
avuti
avute

               | forms of essere, to be (not including the infinitive):
sono
sei
è
siamo
siete
sia
siate
siano
sarò
sarai
sarà
saremo
sarete
saranno
sarei
saresti
sarebbe
saremmo
sareste
sarebbero
ero
eri
era
eravamo
eravate
erano
fui
fosti
fu
fummo
foste
furono
fossi
fosse
fossimo
fossero
essendo

               | forms of fare, to do (not including the infinitive, fa, fat-):
faccio
fai
facciamo
fanno
faccia
facciate
facciano
farò
farai
farà
faremo
farete
faranno
farei
faresti
farebbe
faremmo
fareste
farebbero
facevo
facevi
faceva
facevamo
facevate
facevano
feci
facesti
fece
facemmo
faceste
fecero
facessi
facesse
facessimo
facessero
facendo

               | forms of stare, to be (not including the infinitive):
sto
stai
sta
stiamo
stanno
stia
stiate
stiano
starò
starai
starà
staremo
starete
staranno
starei
staresti
starebbe
staremmo
stareste
starebbero
stavo
stavi
stava
stavamo
stavate
stavano
stetti
stesti
stette
stemmo
steste
stettero
stessi
stesse
stessimo
stessero
''')

js_stemmer = u"""
var JSX={};(function(k){function l(b,e){var a=function(){};a.prototype=e.prototype;var c=new a;for(var d in b){b[d].prototype=c}}function K(c,b){for(var a in b.prototype)if(b.prototype.hasOwnProperty(a))c.prototype[a]=b.prototype[a]}function e(a,b,d){function c(a,b,c){delete a[b];a[b]=c;return c}Object.defineProperty(a,b,{get:function(){return c(a,b,d())},set:function(d){c(a,b,d)},enumerable:true,configurable:true})}function L(a,b,c){return a[b]=a[b]/c|0}var r=parseInt;var B=parseFloat;function M(a){return a!==a}var z=isFinite;var y=encodeURIComponent;var x=decodeURIComponent;var w=encodeURI;var u=decodeURI;var t=Object.prototype.toString;var C=Object.prototype.hasOwnProperty;function j(){}k.require=function(b){var a=q[b];return a!==undefined?a:null};k.profilerIsRunning=function(){return j.getResults!=null};k.getProfileResults=function(){return(j.getResults||function(){return{}})()};k.postProfileResults=function(a,b){if(j.postResults==null)throw new Error('profiler has not been turned on');return j.postResults(a,b)};k.resetProfileResults=function(){if(j.resetResults==null)throw new Error('profiler has not been turned on');return j.resetResults()};k.DEBUG=false;function s(){};l([s],Error);function a(a,b,c){this.F=a.length;this.K=a;this.L=b;this.I=c;this.H=null;this.P=null};l([a],Object);function p(){};l([p],Object);function i(){var a;var b;var c;this.G={};a=this.E='';b=this._=0;c=this.A=a.length;this.D=0;this.C=b;this.B=c};l([i],p);function v(a,b){a.E=b.E;a._=b._;a.A=b.A;a.D=b.D;a.C=b.C;a.B=b.B};function d(b,d,c,e){var a;if(b._>=b.A){return false}a=b.E.charCodeAt(b._);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._++;return true};function m(b,d,c,e){var a;if(b._<=b.D){return false}a=b.E.charCodeAt(b._-1);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._--;return true};function h(a,d,c,e){var b;if(a._>=a.A){return false}b=a.E.charCodeAt(a._);if(b>e||b<c){a._++;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._++;return true}return false};function o(a,b,d){var c;if(a.A-a._<b){return false}if(a.E.slice(c=a._,c+b)!==d){return false}a._+=b;return true};function g(a,b,d){var c;if(a._-a.D<b){return false}if(a.E.slice((c=a._)-b,c)!==d){return false}a._-=b;return true};function n(f,m,p){var b;var d;var e;var n;var g;var k;var l;var i;var h;var c;var a;var j;var o;b=0;d=p;e=f._;n=f.A;g=0;k=0;l=false;while(true){i=b+(d-b>>>1);h=0;c=g<k?g:k;a=m[i];for(j=c;j<a.F;j++){if(e+c===n){h=-1;break}h=f.E.charCodeAt(e+c)-a.K.charCodeAt(j);if(h!==0){break}c++}if(h<0){d=i;k=c}else{b=i;g=c}if(d-b<=1){if(b>0){break}if(d===b){break}if(l){break}l=true}}while(true){a=m[b];if(g>=a.F){f._=e+a.F|0;if(a.H==null){return a.I}o=a.H(a.P);f._=e+a.F|0;if(o){return a.I}}b=a.L;if(b<0){return 0}}return-1};function f(d,m,p){var b;var g;var e;var n;var f;var k;var l;var i;var h;var c;var a;var j;var o;b=0;g=p;e=d._;n=d.D;f=0;k=0;l=false;while(true){i=b+(g-b>>1);h=0;c=f<k?f:k;a=m[i];for(j=a.F-1-c;j>=0;j--){if(e-c===n){h=-1;break}h=d.E.charCodeAt(e-1-c)-a.K.charCodeAt(j);if(h!==0){break}c++}if(h<0){g=i;k=c}else{b=i;f=c}if(g-b<=1){if(b>0){break}if(g===b){break}if(l){break}l=true}}while(true){a=m[b];if(f>=a.F){d._=e-a.F|0;if(a.H==null){return a.I}o=a.H(d);d._=e-a.F|0;if(o){return a.I}}b=a.L;if(b<0){return 0}}return-1};function D(a,b,d,e){var c;c=e.length-(d-b);a.E=a.E.slice(0,b)+e+a.E.slice(d);a.A+=c|0;if(a._>=d){a._+=c|0}else if(a._>b){a._=b}return c|0};function c(a,f){var b;var c;var d;var e;b=false;if((c=a.C)<0||c>(d=a.B)||d>(e=a.A)||e>a.E.length?false:true){D(a,a.C,a.B,f);b=true}return b};i.prototype.J=function(){return false};i.prototype.a=function(b){var a;var c;var d;var e;a=this.G['.'+b];if(a==null){c=this.E=b;d=this._=0;e=this.A=c.length;this.D=0;this.C=d;this.B=e;this.J();a=this.E;this.G['.'+b]=a}return a};i.prototype.stemWord=i.prototype.a;i.prototype.b=function(e){var d;var b;var c;var a;var f;var g;var h;d=[];for(b=0;b<e.length;b++){c=e[b];a=this.G['.'+c];if(a==null){f=this.E=c;g=this._=0;h=this.A=f.length;this.D=0;this.C=g;this.B=h;this.J();a=this.E;this.G['.'+c]=a}d.push(a)}return d};i.prototype.stemWords=i.prototype.b;function b(){i.call(this);this.I_p2=0;this.I_p1=0;this.I_pV=0};l([b],i);b.prototype.M=function(a){this.I_p2=a.I_p2;this.I_p1=a.I_p1;this.I_pV=a.I_pV;v(this,a)};b.prototype.copy_from=b.prototype.M;b.prototype.W=function(){var e;var p;var q;var l;var a;var k;var f;var g;var h;var i;var j;var m;p=this._;b:while(true){q=this._;f=true;a:while(f===true){f=false;this.C=this._;e=n(this,b.a_0,7);if(e===0){break a}this.B=this._;switch(e){case 0:break a;case 1:if(!c(this,'à')){return false}break;case 2:if(!c(this,'è')){return false}break;case 3:if(!c(this,'ì')){return false}break;case 4:if(!c(this,'ò')){return false}break;case 5:if(!c(this,'ù')){return false}break;case 6:if(!c(this,'qU')){return false}break;case 7:if(this._>=this.A){break a}this._++;break}continue b}this._=q;break b}this._=p;b:while(true){l=this._;g=true;d:while(g===true){g=false;e:while(true){a=this._;h=true;a:while(h===true){h=false;if(!d(this,b.g_v,97,249)){break a}this.C=this._;i=true;f:while(i===true){i=false;k=this._;j=true;c:while(j===true){j=false;if(!o(this,1,'u')){break c}this.B=this._;if(!d(this,b.g_v,97,249)){break c}if(!c(this,'U')){return false}break f}this._=k;if(!o(this,1,'i')){break a}this.B=this._;if(!d(this,b.g_v,97,249)){break a}if(!c(this,'I')){return false}}this._=a;break e}m=this._=a;if(m>=this.A){break d}this._++}continue b}this._=l;break b}return true};b.prototype.r_prelude=b.prototype.W;function G(a){var e;var q;var r;var m;var f;var l;var g;var h;var i;var j;var k;var p;q=a._;b:while(true){r=a._;g=true;a:while(g===true){g=false;a.C=a._;e=n(a,b.a_0,7);if(e===0){break a}a.B=a._;switch(e){case 0:break a;case 1:if(!c(a,'à')){return false}break;case 2:if(!c(a,'è')){return false}break;case 3:if(!c(a,'ì')){return false}break;case 4:if(!c(a,'ò')){return false}break;case 5:if(!c(a,'ù')){return false}break;case 6:if(!c(a,'qU')){return false}break;case 7:if(a._>=a.A){break a}a._++;break}continue b}a._=r;break b}a._=q;b:while(true){m=a._;h=true;d:while(h===true){h=false;e:while(true){f=a._;i=true;a:while(i===true){i=false;if(!d(a,b.g_v,97,249)){break a}a.C=a._;j=true;f:while(j===true){j=false;l=a._;k=true;c:while(k===true){k=false;if(!o(a,1,'u')){break c}a.B=a._;if(!d(a,b.g_v,97,249)){break c}if(!c(a,'U')){return false}break f}a._=l;if(!o(a,1,'i')){break a}a.B=a._;if(!d(a,b.g_v,97,249)){break a}if(!c(a,'I')){return false}}a._=f;break e}p=a._=f;if(p>=a.A){break d}a._++}continue b}a._=m;break b}return true};b.prototype.U=function(){var u;var w;var x;var y;var t;var l;var e;var f;var g;var i;var c;var j;var k;var a;var m;var n;var o;var p;var q;var r;var s;var v;this.I_pV=s=this.A;this.I_p1=s;this.I_p2=s;u=this._;l=true;a:while(l===true){l=false;e=true;g:while(e===true){e=false;w=this._;f=true;b:while(f===true){f=false;if(!d(this,b.g_v,97,249)){break b}g=true;f:while(g===true){g=false;x=this._;i=true;c:while(i===true){i=false;if(!h(this,b.g_v,97,249)){break c}d:while(true){c=true;e:while(c===true){c=false;if(!d(this,b.g_v,97,249)){break e}break d}if(this._>=this.A){break c}this._++}break f}this._=x;if(!d(this,b.g_v,97,249)){break b}c:while(true){j=true;d:while(j===true){j=false;if(!h(this,b.g_v,97,249)){break d}break c}if(this._>=this.A){break b}this._++}}break g}this._=w;if(!h(this,b.g_v,97,249)){break a}k=true;c:while(k===true){k=false;y=this._;a=true;b:while(a===true){a=false;if(!h(this,b.g_v,97,249)){break b}e:while(true){m=true;d:while(m===true){m=false;if(!d(this,b.g_v,97,249)){break d}break e}if(this._>=this.A){break b}this._++}break c}this._=y;if(!d(this,b.g_v,97,249)){break a}if(this._>=this.A){break a}this._++}}this.I_pV=this._}v=this._=u;t=v;n=true;a:while(n===true){n=false;b:while(true){o=true;c:while(o===true){o=false;if(!d(this,b.g_v,97,249)){break c}break b}if(this._>=this.A){break a}this._++}b:while(true){p=true;c:while(p===true){p=false;if(!h(this,b.g_v,97,249)){break c}break b}if(this._>=this.A){break a}this._++}this.I_p1=this._;b:while(true){q=true;c:while(q===true){q=false;if(!d(this,b.g_v,97,249)){break c}break b}if(this._>=this.A){break a}this._++}c:while(true){r=true;b:while(r===true){r=false;if(!h(this,b.g_v,97,249)){break b}break c}if(this._>=this.A){break a}this._++}this.I_p2=this._}this._=t;return true};b.prototype.r_mark_regions=b.prototype.U;function H(a){var x;var y;var z;var u;var v;var l;var e;var f;var g;var i;var j;var k;var c;var m;var n;var o;var p;var q;var r;var s;var t;var w;a.I_pV=t=a.A;a.I_p1=t;a.I_p2=t;x=a._;l=true;a:while(l===true){l=false;e=true;g:while(e===true){e=false;y=a._;f=true;b:while(f===true){f=false;if(!d(a,b.g_v,97,249)){break b}g=true;f:while(g===true){g=false;z=a._;i=true;c:while(i===true){i=false;if(!h(a,b.g_v,97,249)){break c}d:while(true){j=true;e:while(j===true){j=false;if(!d(a,b.g_v,97,249)){break e}break d}if(a._>=a.A){break c}a._++}break f}a._=z;if(!d(a,b.g_v,97,249)){break b}c:while(true){k=true;d:while(k===true){k=false;if(!h(a,b.g_v,97,249)){break d}break c}if(a._>=a.A){break b}a._++}}break g}a._=y;if(!h(a,b.g_v,97,249)){break a}c=true;c:while(c===true){c=false;u=a._;m=true;b:while(m===true){m=false;if(!h(a,b.g_v,97,249)){break b}e:while(true){n=true;d:while(n===true){n=false;if(!d(a,b.g_v,97,249)){break d}break e}if(a._>=a.A){break b}a._++}break c}a._=u;if(!d(a,b.g_v,97,249)){break a}if(a._>=a.A){break a}a._++}}a.I_pV=a._}w=a._=x;v=w;o=true;a:while(o===true){o=false;b:while(true){p=true;c:while(p===true){p=false;if(!d(a,b.g_v,97,249)){break c}break b}if(a._>=a.A){break a}a._++}b:while(true){q=true;c:while(q===true){q=false;if(!h(a,b.g_v,97,249)){break c}break b}if(a._>=a.A){break a}a._++}a.I_p1=a._;b:while(true){r=true;c:while(r===true){r=false;if(!d(a,b.g_v,97,249)){break c}break b}if(a._>=a.A){break a}a._++}c:while(true){s=true;b:while(s===true){s=false;if(!h(a,b.g_v,97,249)){break b}break c}if(a._>=a.A){break a}a._++}a.I_p2=a._}a._=v;return true};b.prototype.V=function(){var a;var e;var d;b:while(true){e=this._;d=true;a:while(d===true){d=false;this.C=this._;a=n(this,b.a_1,3);if(a===0){break a}this.B=this._;switch(a){case 0:break a;case 1:if(!c(this,'i')){return false}break;case 2:if(!c(this,'u')){return false}break;case 3:if(this._>=this.A){break a}this._++;break}continue b}this._=e;break b}return true};b.prototype.r_postlude=b.prototype.V;function I(a){var d;var f;var e;b:while(true){f=a._;e=true;a:while(e===true){e=false;a.C=a._;d=n(a,b.a_1,3);if(d===0){break a}a.B=a._;switch(d){case 0:break a;case 1:if(!c(a,'i')){return false}break;case 2:if(!c(a,'u')){return false}break;case 3:if(a._>=a.A){break a}a._++;break}continue b}a._=f;break b}return true};b.prototype.S=function(){return!(this.I_pV<=this._)?false:true};b.prototype.r_RV=b.prototype.S;b.prototype.Q=function(){return!(this.I_p1<=this._)?false:true};b.prototype.r_R1=b.prototype.Q;b.prototype.R=function(){return!(this.I_p2<=this._)?false:true};b.prototype.r_R2=b.prototype.R;b.prototype.T=function(){var a;this.B=this._;if(f(this,b.a_2,37)===0){return false}this.C=this._;a=f(this,b.a_3,5);if(a===0){return false}if(!(!(this.I_pV<=this._)?false:true)){return false}switch(a){case 0:return false;case 1:if(!c(this,'')){return false}break;case 2:if(!c(this,'e')){return false}break}return true};b.prototype.r_attached_pronoun=b.prototype.T;function J(a){var d;a.B=a._;if(f(a,b.a_2,37)===0){return false}a.C=a._;d=f(a,b.a_3,5);if(d===0){return false}if(!(!(a.I_pV<=a._)?false:true)){return false}switch(d){case 0:return false;case 1:if(!c(a,'')){return false}break;case 2:if(!c(a,'e')){return false}break}return true};b.prototype.X=function(){var a;var j;var d;var h;var e;var k;var i;var l;var m;var o;var p;var q;var r;var n;this.B=this._;a=f(this,b.a_6,51);if(a===0){return false}this.C=this._;switch(a){case 0:return false;case 1:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}break;case 2:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}j=this.A-this._;k=true;a:while(k===true){k=false;this.B=this._;if(!g(this,2,'ic')){this._=this.A-j;break a}this.C=o=this._;if(!(!(this.I_p2<=o)?false:true)){this._=this.A-j;break a}if(!c(this,'')){return false}}break;case 3:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'log')){return false}break;case 4:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'u')){return false}break;case 5:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'ente')){return false}break;case 6:if(!(!(this.I_pV<=this._)?false:true)){return false}if(!c(this,'')){return false}break;case 7:if(!(!(this.I_p1<=this._)?false:true)){return false}if(!c(this,'')){return false}d=this.A-this._;i=true;a:while(i===true){i=false;this.B=this._;a=f(this,b.a_4,4);if(a===0){this._=this.A-d;break a}this.C=p=this._;if(!(!(this.I_p2<=p)?false:true)){this._=this.A-d;break a}if(!c(this,'')){return false}switch(a){case 0:this._=this.A-d;break a;case 1:this.B=this._;if(!g(this,2,'at')){this._=this.A-d;break a}this.C=q=this._;if(!(!(this.I_p2<=q)?false:true)){this._=this.A-d;break a}if(!c(this,'')){return false}break}}break;case 8:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}h=this.A-this._;l=true;a:while(l===true){l=false;this.B=this._;a=f(this,b.a_5,3);if(a===0){this._=this.A-h;break a}this.C=this._;switch(a){case 0:this._=this.A-h;break a;case 1:if(!(!(this.I_p2<=this._)?false:true)){this._=this.A-h;break a}if(!c(this,'')){return false}break}}break;case 9:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}e=this.A-this._;m=true;a:while(m===true){m=false;this.B=this._;if(!g(this,2,'at')){this._=this.A-e;break a}this.C=r=this._;if(!(!(this.I_p2<=r)?false:true)){this._=this.A-e;break a}if(!c(this,'')){return false}this.B=this._;if(!g(this,2,'ic')){this._=this.A-e;break a}this.C=n=this._;if(!(!(this.I_p2<=n)?false:true)){this._=this.A-e;break a}if(!c(this,'')){return false}}break}return true};b.prototype.r_standard_suffix=b.prototype.X;function F(a){var d;var k;var e;var i;var h;var l;var j;var m;var n;var p;var q;var r;var s;var o;a.B=a._;d=f(a,b.a_6,51);if(d===0){return false}a.C=a._;switch(d){case 0:return false;case 1:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}break;case 2:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}k=a.A-a._;l=true;a:while(l===true){l=false;a.B=a._;if(!g(a,2,'ic')){a._=a.A-k;break a}a.C=p=a._;if(!(!(a.I_p2<=p)?false:true)){a._=a.A-k;break a}if(!c(a,'')){return false}}break;case 3:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'log')){return false}break;case 4:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'u')){return false}break;case 5:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'ente')){return false}break;case 6:if(!(!(a.I_pV<=a._)?false:true)){return false}if(!c(a,'')){return false}break;case 7:if(!(!(a.I_p1<=a._)?false:true)){return false}if(!c(a,'')){return false}e=a.A-a._;j=true;a:while(j===true){j=false;a.B=a._;d=f(a,b.a_4,4);if(d===0){a._=a.A-e;break a}a.C=q=a._;if(!(!(a.I_p2<=q)?false:true)){a._=a.A-e;break a}if(!c(a,'')){return false}switch(d){case 0:a._=a.A-e;break a;case 1:a.B=a._;if(!g(a,2,'at')){a._=a.A-e;break a}a.C=r=a._;if(!(!(a.I_p2<=r)?false:true)){a._=a.A-e;break a}if(!c(a,'')){return false}break}}break;case 8:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}i=a.A-a._;m=true;a:while(m===true){m=false;a.B=a._;d=f(a,b.a_5,3);if(d===0){a._=a.A-i;break a}a.C=a._;switch(d){case 0:a._=a.A-i;break a;case 1:if(!(!(a.I_p2<=a._)?false:true)){a._=a.A-i;break a}if(!c(a,'')){return false}break}}break;case 9:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}h=a.A-a._;n=true;a:while(n===true){n=false;a.B=a._;if(!g(a,2,'at')){a._=a.A-h;break a}a.C=s=a._;if(!(!(a.I_p2<=s)?false:true)){a._=a.A-h;break a}if(!c(a,'')){return false}a.B=a._;if(!g(a,2,'ic')){a._=a.A-h;break a}a.C=o=a._;if(!(!(a.I_p2<=o)?false:true)){a._=a.A-h;break a}if(!c(a,'')){return false}}break}return true};b.prototype.Y=function(){var d;var e;var a;var g;var h;var i;e=this.A-(g=this._);if(g<this.I_pV){return false}h=this._=this.I_pV;a=this.D;this.D=h;i=this._=this.A-e;this.B=i;d=f(this,b.a_7,87);if(d===0){this.D=a;return false}this.C=this._;switch(d){case 0:this.D=a;return false;case 1:if(!c(this,'')){return false}break}this.D=a;return true};b.prototype.r_verb_suffix=b.prototype.Y;function E(a){var e;var g;var d;var h;var i;var j;g=a.A-(h=a._);if(h<a.I_pV){return false}i=a._=a.I_pV;d=a.D;a.D=i;j=a._=a.A-g;a.B=j;e=f(a,b.a_7,87);if(e===0){a.D=d;return false}a.C=a._;switch(e){case 0:a.D=d;return false;case 1:if(!c(a,'')){return false}break}a.D=d;return true};b.prototype.Z=function(){var a;var d;var e;var f;var h;var i;a=this.A-this._;e=true;a:while(e===true){e=false;this.B=this._;if(!m(this,b.g_AEIO,97,242)){this._=this.A-a;break a}this.C=h=this._;if(!(!(this.I_pV<=h)?false:true)){this._=this.A-a;break a}if(!c(this,'')){return false}this.B=this._;if(!g(this,1,'i')){this._=this.A-a;break a}this.C=i=this._;if(!(!(this.I_pV<=i)?false:true)){this._=this.A-a;break a}if(!c(this,'')){return false}}d=this.A-this._;f=true;a:while(f===true){f=false;this.B=this._;if(!g(this,1,'h')){this._=this.A-d;break a}this.C=this._;if(!m(this,b.g_CG,99,103)){this._=this.A-d;break a}if(!(!(this.I_pV<=this._)?false:true)){this._=this.A-d;break a}if(!c(this,'')){return false}}return true};b.prototype.r_vowel_suffix=b.prototype.Z;function A(a){var d;var e;var f;var h;var i;var j;d=a.A-a._;f=true;a:while(f===true){f=false;a.B=a._;if(!m(a,b.g_AEIO,97,242)){a._=a.A-d;break a}a.C=i=a._;if(!(!(a.I_pV<=i)?false:true)){a._=a.A-d;break a}if(!c(a,'')){return false}a.B=a._;if(!g(a,1,'i')){a._=a.A-d;break a}a.C=j=a._;if(!(!(a.I_pV<=j)?false:true)){a._=a.A-d;break a}if(!c(a,'')){return false}}e=a.A-a._;h=true;a:while(h===true){h=false;a.B=a._;if(!g(a,1,'h')){a._=a.A-e;break a}a.C=a._;if(!m(a,b.g_CG,99,103)){a._=a.A-e;break a}if(!(!(a.I_pV<=a._)?false:true)){a._=a.A-e;break a}if(!c(a,'')){return false}}return true};b.prototype.J=function(){var l;var i;var j;var k;var m;var n;var b;var c;var d;var e;var a;var f;var g;var h;var p;var q;var r;var s;var t;var u;var o;l=this._;b=true;a:while(b===true){b=false;if(!G(this)){break a}}p=this._=l;i=p;c=true;a:while(c===true){c=false;if(!H(this)){break a}}q=this._=i;this.D=q;s=this._=r=this.A;j=r-s;d=true;a:while(d===true){d=false;if(!J(this)){break a}}u=this._=(t=this.A)-j;k=t-u;e=true;a:while(e===true){e=false;a=true;b:while(a===true){a=false;m=this.A-this._;f=true;c:while(f===true){f=false;if(!F(this)){break c}break b}this._=this.A-m;if(!E(this)){break a}}}this._=this.A-k;g=true;a:while(g===true){g=false;if(!A(this)){break a}}o=this._=this.D;n=o;h=true;a:while(h===true){h=false;if(!I(this)){break a}}this._=n;return true};b.prototype.stem=b.prototype.J;b.prototype.N=function(a){return a instanceof b};b.prototype.equals=b.prototype.N;b.prototype.O=function(){var c;var a;var b;var d;c='ItalianStemmer';a=0;for(b=0;b<c.length;b++){d=c.charCodeAt(b);a=(a<<5)-a+d;a=a&a}return a|0};b.prototype.hashCode=b.prototype.O;b.serialVersionUID=1;e(b,'methodObject',function(){return new b});e(b,'a_0',function(){return[new a('',-1,7),new a('qu',0,6),new a('á',0,1),new a('é',0,2),new a('í',0,3),new a('ó',0,4),new a('ú',0,5)]});e(b,'a_1',function(){return[new a('',-1,3),new a('I',0,1),new a('U',0,2)]});e(b,'a_2',function(){return[new a('la',-1,-1),new a('cela',0,-1),new a('gliela',0,-1),new a('mela',0,-1),new a('tela',0,-1),new a('vela',0,-1),new a('le',-1,-1),new a('cele',6,-1),new a('gliele',6,-1),new a('mele',6,-1),new a('tele',6,-1),new a('vele',6,-1),new a('ne',-1,-1),new a('cene',12,-1),new a('gliene',12,-1),new a('mene',12,-1),new a('sene',12,-1),new a('tene',12,-1),new a('vene',12,-1),new a('ci',-1,-1),new a('li',-1,-1),new a('celi',20,-1),new a('glieli',20,-1),new a('meli',20,-1),new a('teli',20,-1),new a('veli',20,-1),new a('gli',20,-1),new a('mi',-1,-1),new a('si',-1,-1),new a('ti',-1,-1),new a('vi',-1,-1),new a('lo',-1,-1),new a('celo',31,-1),new a('glielo',31,-1),new a('melo',31,-1),new a('telo',31,-1),new a('velo',31,-1)]});e(b,'a_3',function(){return[new a('ando',-1,1),new a('endo',-1,1),new a('ar',-1,2),new a('er',-1,2),new a('ir',-1,2)]});e(b,'a_4',function(){return[new a('ic',-1,-1),new a('abil',-1,-1),new a('os',-1,-1),new a('iv',-1,1)]});e(b,'a_5',function(){return[new a('ic',-1,1),new a('abil',-1,1),new a('iv',-1,1)]});e(b,'a_6',function(){return[new a('ica',-1,1),new a('logia',-1,3),new a('osa',-1,1),new a('ista',-1,1),new a('iva',-1,9),new a('anza',-1,1),new a('enza',-1,5),new a('ice',-1,1),new a('atrice',7,1),new a('iche',-1,1),new a('logie',-1,3),new a('abile',-1,1),new a('ibile',-1,1),new a('usione',-1,4),new a('azione',-1,2),new a('uzione',-1,4),new a('atore',-1,2),new a('ose',-1,1),new a('ante',-1,1),new a('mente',-1,1),new a('amente',19,7),new a('iste',-1,1),new a('ive',-1,9),new a('anze',-1,1),new a('enze',-1,5),new a('ici',-1,1),new a('atrici',25,1),new a('ichi',-1,1),new a('abili',-1,1),new a('ibili',-1,1),new a('ismi',-1,1),new a('usioni',-1,4),new a('azioni',-1,2),new a('uzioni',-1,4),new a('atori',-1,2),new a('osi',-1,1),new a('anti',-1,1),new a('amenti',-1,6),new a('imenti',-1,6),new a('isti',-1,1),new a('ivi',-1,9),new a('ico',-1,1),new a('ismo',-1,1),new a('oso',-1,1),new a('amento',-1,6),new a('imento',-1,6),new a('ivo',-1,9),new a('ità',-1,8),new a('istà',-1,1),new a('istè',-1,1),new a('istì',-1,1)]});e(b,'a_7',function(){return[new a('isca',-1,1),new a('enda',-1,1),new a('ata',-1,1),new a('ita',-1,1),new a('uta',-1,1),new a('ava',-1,1),new a('eva',-1,1),new a('iva',-1,1),new a('erebbe',-1,1),new a('irebbe',-1,1),new a('isce',-1,1),new a('ende',-1,1),new a('are',-1,1),new a('ere',-1,1),new a('ire',-1,1),new a('asse',-1,1),new a('ate',-1,1),new a('avate',16,1),new a('evate',16,1),new a('ivate',16,1),new a('ete',-1,1),new a('erete',20,1),new a('irete',20,1),new a('ite',-1,1),new a('ereste',-1,1),new a('ireste',-1,1),new a('ute',-1,1),new a('erai',-1,1),new a('irai',-1,1),new a('isci',-1,1),new a('endi',-1,1),new a('erei',-1,1),new a('irei',-1,1),new a('assi',-1,1),new a('ati',-1,1),new a('iti',-1,1),new a('eresti',-1,1),new a('iresti',-1,1),new a('uti',-1,1),new a('avi',-1,1),new a('evi',-1,1),new a('ivi',-1,1),new a('isco',-1,1),new a('ando',-1,1),new a('endo',-1,1),new a('Yamo',-1,1),new a('iamo',-1,1),new a('avamo',-1,1),new a('evamo',-1,1),new a('ivamo',-1,1),new a('eremo',-1,1),new a('iremo',-1,1),new a('assimo',-1,1),new a('ammo',-1,1),new a('emmo',-1,1),new a('eremmo',54,1),new a('iremmo',54,1),new a('immo',-1,1),new a('ano',-1,1),new a('iscano',58,1),new a('avano',58,1),new a('evano',58,1),new a('ivano',58,1),new a('eranno',-1,1),new a('iranno',-1,1),new a('ono',-1,1),new a('iscono',65,1),new a('arono',65,1),new a('erono',65,1),new a('irono',65,1),new a('erebbero',-1,1),new a('irebbero',-1,1),new a('assero',-1,1),new a('essero',-1,1),new a('issero',-1,1),new a('ato',-1,1),new a('ito',-1,1),new a('uto',-1,1),new a('avo',-1,1),new a('evo',-1,1),new a('ivo',-1,1),new a('ar',-1,1),new a('ir',-1,1),new a('erà',-1,1),new a('irà',-1,1),new a('erò',-1,1),new a('irò',-1,1)]});e(b,'g_v',function(){return[17,65,16,0,0,0,0,0,0,0,0,0,0,0,0,128,128,8,2,1]});e(b,'g_AEIO',function(){return[17,65,0,0,0,0,0,0,0,0,0,0,0,0,0,128,128,8,2]});e(b,'g_CG',function(){return[17]});var q={'src/stemmer.jsx':{Stemmer:p},'src/italian-stemmer.jsx':{ItalianStemmer:b}}}(JSX))
var Stemmer = JSX.require("src/italian-stemmer.jsx").ItalianStemmer;
"""


class SearchItalian(SearchLanguage):
    lang = 'it'
    language_name = 'Italian'
    js_stemmer_rawcode = 'italian-stemmer.js'
    js_stemmer_code = js_stemmer
    stopwords = italian_stopwords

    def init(self, options):
        # type: (Any) -> None
        self.stemmer = snowballstemmer.stemmer('italian')

    def stem(self, word):
        # type: (unicode) -> unicode
        return self.stemmer.stemWord(word.lower())
