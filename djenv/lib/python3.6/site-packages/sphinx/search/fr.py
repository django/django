# -*- coding: utf-8 -*-
"""
    sphinx.search.fr
    ~~~~~~~~~~~~~~~~

    French search language: includes the JS French stemmer.

    :copyright: Copyright 2007-2013 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from sphinx.search import SearchLanguage, parse_stop_word

import snowballstemmer

if False:
    # For type annotation
    from typing import Any  # NOQA


french_stopwords = parse_stop_word(u'''
| source: http://snowball.tartarus.org/algorithms/french/stop.txt
au             |  a + le
aux            |  a + les
avec           |  with
ce             |  this
ces            |  these
dans           |  with
de             |  of
des            |  de + les
du             |  de + le
elle           |  she
en             |  `of them' etc
et             |  and
eux            |  them
il             |  he
je             |  I
la             |  the
le             |  the
leur           |  their
lui            |  him
ma             |  my (fem)
mais           |  but
me             |  me
même           |  same; as in moi-même (myself) etc
mes            |  me (pl)
moi            |  me
mon            |  my (masc)
ne             |  not
nos            |  our (pl)
notre          |  our
nous           |  we
on             |  one
ou             |  where
par            |  by
pas            |  not
pour           |  for
qu             |  que before vowel
que            |  that
qui            |  who
sa             |  his, her (fem)
se             |  oneself
ses            |  his (pl)
son            |  his, her (masc)
sur            |  on
ta             |  thy (fem)
te             |  thee
tes            |  thy (pl)
toi            |  thee
ton            |  thy (masc)
tu             |  thou
un             |  a
une            |  a
vos            |  your (pl)
votre          |  your
vous           |  you

               |  single letter forms

c              |  c'
d              |  d'
j              |  j'
l              |  l'
à              |  to, at
m              |  m'
n              |  n'
s              |  s'
t              |  t'
y              |  there

               | forms of être (not including the infinitive):
été
étée
étées
étés
étant
suis
es
est
sommes
êtes
sont
serai
seras
sera
serons
serez
seront
serais
serait
serions
seriez
seraient
étais
était
étions
étiez
étaient
fus
fut
fûmes
fûtes
furent
sois
soit
soyons
soyez
soient
fusse
fusses
fût
fussions
fussiez
fussent

               | forms of avoir (not including the infinitive):
ayant
eu
eue
eues
eus
ai
as
avons
avez
ont
aurai
auras
aura
aurons
aurez
auront
aurais
aurait
aurions
auriez
auraient
avais
avait
avions
aviez
avaient
eut
eûmes
eûtes
eurent
aie
aies
ait
ayons
ayez
aient
eusse
eusses
eût
eussions
eussiez
eussent

               | Later additions (from Jean-Christophe Deschamps)
ceci           |  this
cela           |  that (added 11 Apr 2012. Omission reported by Adrien Grand)
celà           |  that (incorrect, though common)
cet            |  this
cette          |  this
ici            |  here
ils            |  they
les            |  the (pl)
leurs          |  their (pl)
quel           |  which
quels          |  which
quelle         |  which
quelles        |  which
sans           |  without
soi            |  oneself
''')

js_stemmer = u"""
var JSX={};(function(l){function m(b,e){var a=function(){};a.prototype=e.prototype;var c=new a;for(var d in b){b[d].prototype=c}}function P(c,b){for(var a in b.prototype)if(b.prototype.hasOwnProperty(a))c.prototype[a]=b.prototype[a]}function g(a,b,d){function c(a,b,c){delete a[b];a[b]=c;return c}Object.defineProperty(a,b,{get:function(){return c(a,b,d())},set:function(d){c(a,b,d)},enumerable:true,configurable:true})}function O(a,b,c){return a[b]=a[b]/c|0}var u=parseInt;var v=parseFloat;function N(a){return a!==a}var x=isFinite;var y=encodeURIComponent;var z=decodeURIComponent;var A=encodeURI;var B=decodeURI;var C=Object.prototype.toString;var D=Object.prototype.hasOwnProperty;function k(){}l.require=function(b){var a=q[b];return a!==undefined?a:null};l.profilerIsRunning=function(){return k.getResults!=null};l.getProfileResults=function(){return(k.getResults||function(){return{}})()};l.postProfileResults=function(a,b){if(k.postResults==null)throw new Error('profiler has not been turned on');return k.postResults(a,b)};l.resetProfileResults=function(){if(k.resetResults==null)throw new Error('profiler has not been turned on');return k.resetResults()};l.DEBUG=false;function G(){};m([G],Error);function a(a,b,c){this.F=a.length;this.K=a;this.L=b;this.I=c;this.H=null;this.P=null};m([a],Object);function p(){};m([p],Object);function i(){var a;var b;var c;this.G={};a=this.E='';b=this._=0;c=this.A=a.length;this.B=0;this.D=b;this.C=c};m([i],p);function s(a,b){a.E=b.E;a._=b._;a.A=b.A;a.B=b.B;a.D=b.D;a.C=b.C};function e(b,d,c,e){var a;if(b._>=b.A){return false}a=b.E.charCodeAt(b._);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._++;return true};function r(b,d,c,e){var a;if(b._<=b.B){return false}a=b.E.charCodeAt(b._-1);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._--;return true};function o(a,d,c,e){var b;if(a._>=a.A){return false}b=a.E.charCodeAt(a._);if(b>e||b<c){a._++;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._++;return true}return false};function j(a,d,c,e){var b;if(a._<=a.B){return false}b=a.E.charCodeAt(a._-1);if(b>e||b<c){a._--;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._--;return true}return false};function h(a,b,d){var c;if(a.A-a._<b){return false}if(a.E.slice(c=a._,c+b)!==d){return false}a._+=b;return true};function d(a,b,d){var c;if(a._-a.B<b){return false}if(a.E.slice((c=a._)-b,c)!==d){return false}a._-=b;return true};function n(f,m,p){var b;var d;var e;var n;var g;var k;var l;var i;var h;var c;var a;var j;var o;b=0;d=p;e=f._;n=f.A;g=0;k=0;l=false;while(true){i=b+(d-b>>>1);h=0;c=g<k?g:k;a=m[i];for(j=c;j<a.F;j++){if(e+c===n){h=-1;break}h=f.E.charCodeAt(e+c)-a.K.charCodeAt(j);if(h!==0){break}c++}if(h<0){d=i;k=c}else{b=i;g=c}if(d-b<=1){if(b>0){break}if(d===b){break}if(l){break}l=true}}while(true){a=m[b];if(g>=a.F){f._=e+a.F|0;if(a.H==null){return a.I}o=a.H(a.P);f._=e+a.F|0;if(o){return a.I}}b=a.L;if(b<0){return 0}}return-1};function f(d,m,p){var b;var g;var e;var n;var f;var k;var l;var i;var h;var c;var a;var j;var o;b=0;g=p;e=d._;n=d.B;f=0;k=0;l=false;while(true){i=b+(g-b>>1);h=0;c=f<k?f:k;a=m[i];for(j=a.F-1-c;j>=0;j--){if(e-c===n){h=-1;break}h=d.E.charCodeAt(e-1-c)-a.K.charCodeAt(j);if(h!==0){break}c++}if(h<0){g=i;k=c}else{b=i;f=c}if(g-b<=1){if(b>0){break}if(g===b){break}if(l){break}l=true}}while(true){a=m[b];if(f>=a.F){d._=e-a.F|0;if(a.H==null){return a.I}o=a.H(d);d._=e-a.F|0;if(o){return a.I}}b=a.L;if(b<0){return 0}}return-1};function E(a,b,d,e){var c;c=e.length-(d-b);a.E=a.E.slice(0,b)+e+a.E.slice(d);a.A+=c|0;if(a._>=d){a._+=c|0}else if(a._>b){a._=b}return c|0};function c(a,f){var b;var c;var d;var e;b=false;if((c=a.D)<0||c>(d=a.C)||d>(e=a.A)||e>a.E.length?false:true){E(a,a.D,a.C,f);b=true}return b};i.prototype.J=function(){return false};i.prototype.c=function(b){var a;var c;var d;var e;a=this.G['.'+b];if(a==null){c=this.E=b;d=this._=0;e=this.A=c.length;this.B=0;this.D=d;this.C=e;this.J();a=this.E;this.G['.'+b]=a}return a};i.prototype.stemWord=i.prototype.c;i.prototype.d=function(e){var d;var b;var c;var a;var f;var g;var h;d=[];for(b=0;b<e.length;b++){c=e[b];a=this.G['.'+c];if(a==null){f=this.E=c;g=this._=0;h=this.A=f.length;this.B=0;this.D=g;this.C=h;this.J();a=this.E;this.G['.'+c]=a}d.push(a)}return d};i.prototype.stemWords=i.prototype.d;function b(){i.call(this);this.I_p2=0;this.I_p1=0;this.I_pV=0};m([b],i);b.prototype.M=function(a){this.I_p2=a.I_p2;this.I_p1=a.I_p1;this.I_pV=a.I_pV;s(this,a)};b.prototype.copy_from=b.prototype.M;b.prototype.W=function(){var p;var j;var f;var g;var i;var a;var d;var k;var l;var m;var n;var o;var q;a:while(true){p=this._;i=true;g:while(i===true){i=false;h:while(true){j=this._;a=true;b:while(a===true){a=false;d=true;c:while(d===true){d=false;f=this._;k=true;d:while(k===true){k=false;if(!e(this,b.g_v,97,251)){break d}this.D=this._;l=true;e:while(l===true){l=false;g=this._;m=true;f:while(m===true){m=false;if(!h(this,1,'u')){break f}this.C=this._;if(!e(this,b.g_v,97,251)){break f}if(!c(this,'U')){return false}break e}this._=g;n=true;f:while(n===true){n=false;if(!h(this,1,'i')){break f}this.C=this._;if(!e(this,b.g_v,97,251)){break f}if(!c(this,'I')){return false}break e}this._=g;if(!h(this,1,'y')){break d}this.C=this._;if(!c(this,'Y')){return false}}break c}this._=f;o=true;d:while(o===true){o=false;this.D=this._;if(!h(this,1,'y')){break d}this.C=this._;if(!e(this,b.g_v,97,251)){break d}if(!c(this,'Y')){return false}break c}this._=f;if(!h(this,1,'q')){break b}this.D=this._;if(!h(this,1,'u')){break b}this.C=this._;if(!c(this,'U')){return false}}this._=j;break h}q=this._=j;if(q>=this.A){break g}this._++}continue a}this._=p;break a}return true};b.prototype.r_prelude=b.prototype.W;function H(a){var q;var k;var f;var g;var i;var j;var d;var l;var m;var n;var o;var p;var r;a:while(true){q=a._;i=true;g:while(i===true){i=false;h:while(true){k=a._;j=true;b:while(j===true){j=false;d=true;c:while(d===true){d=false;f=a._;l=true;d:while(l===true){l=false;if(!e(a,b.g_v,97,251)){break d}a.D=a._;m=true;e:while(m===true){m=false;g=a._;n=true;f:while(n===true){n=false;if(!h(a,1,'u')){break f}a.C=a._;if(!e(a,b.g_v,97,251)){break f}if(!c(a,'U')){return false}break e}a._=g;o=true;f:while(o===true){o=false;if(!h(a,1,'i')){break f}a.C=a._;if(!e(a,b.g_v,97,251)){break f}if(!c(a,'I')){return false}break e}a._=g;if(!h(a,1,'y')){break d}a.C=a._;if(!c(a,'Y')){return false}}break c}a._=f;p=true;d:while(p===true){p=false;a.D=a._;if(!h(a,1,'y')){break d}a.C=a._;if(!e(a,b.g_v,97,251)){break d}if(!c(a,'Y')){return false}break c}a._=f;if(!h(a,1,'q')){break b}a.D=a._;if(!h(a,1,'u')){break b}a.C=a._;if(!c(a,'U')){return false}}a._=k;break h}r=a._=k;if(r>=a.A){break g}a._++}continue a}a._=q;break a}return true};b.prototype.U=function(){var t;var i;var r;var d;var f;var g;var h;var c;var a;var j;var k;var l;var m;var s;var p;var q;this.I_pV=p=this.A;this.I_p1=p;this.I_p2=p;t=this._;d=true;b:while(d===true){d=false;f=true;c:while(f===true){f=false;i=this._;g=true;a:while(g===true){g=false;if(!e(this,b.g_v,97,251)){break a}if(!e(this,b.g_v,97,251)){break a}if(this._>=this.A){break a}this._++;break c}this._=i;h=true;a:while(h===true){h=false;if(n(this,b.a_0,3)===0){break a}break c}s=this._=i;if(s>=this.A){break b}this._++;a:while(true){c=true;d:while(c===true){c=false;if(!e(this,b.g_v,97,251)){break d}break a}if(this._>=this.A){break b}this._++}}this.I_pV=this._}q=this._=t;r=q;a=true;a:while(a===true){a=false;c:while(true){j=true;b:while(j===true){j=false;if(!e(this,b.g_v,97,251)){break b}break c}if(this._>=this.A){break a}this._++}b:while(true){k=true;c:while(k===true){k=false;if(!o(this,b.g_v,97,251)){break c}break b}if(this._>=this.A){break a}this._++}this.I_p1=this._;b:while(true){l=true;c:while(l===true){l=false;if(!e(this,b.g_v,97,251)){break c}break b}if(this._>=this.A){break a}this._++}c:while(true){m=true;b:while(m===true){m=false;if(!o(this,b.g_v,97,251)){break b}break c}if(this._>=this.A){break a}this._++}this.I_p2=this._}this._=r;return true};b.prototype.r_mark_regions=b.prototype.U;function I(a){var s;var i;var r;var d;var f;var g;var h;var c;var j;var k;var l;var m;var p;var t;var q;var u;a.I_pV=q=a.A;a.I_p1=q;a.I_p2=q;s=a._;d=true;b:while(d===true){d=false;f=true;c:while(f===true){f=false;i=a._;g=true;a:while(g===true){g=false;if(!e(a,b.g_v,97,251)){break a}if(!e(a,b.g_v,97,251)){break a}if(a._>=a.A){break a}a._++;break c}a._=i;h=true;a:while(h===true){h=false;if(n(a,b.a_0,3)===0){break a}break c}t=a._=i;if(t>=a.A){break b}a._++;a:while(true){c=true;d:while(c===true){c=false;if(!e(a,b.g_v,97,251)){break d}break a}if(a._>=a.A){break b}a._++}}a.I_pV=a._}u=a._=s;r=u;j=true;a:while(j===true){j=false;c:while(true){k=true;b:while(k===true){k=false;if(!e(a,b.g_v,97,251)){break b}break c}if(a._>=a.A){break a}a._++}b:while(true){l=true;c:while(l===true){l=false;if(!o(a,b.g_v,97,251)){break c}break b}if(a._>=a.A){break a}a._++}a.I_p1=a._;b:while(true){m=true;c:while(m===true){m=false;if(!e(a,b.g_v,97,251)){break c}break b}if(a._>=a.A){break a}a._++}c:while(true){p=true;b:while(p===true){p=false;if(!o(a,b.g_v,97,251)){break b}break c}if(a._>=a.A){break a}a._++}a.I_p2=a._}a._=r;return true};b.prototype.V=function(){var a;var e;var d;b:while(true){e=this._;d=true;a:while(d===true){d=false;this.D=this._;a=n(this,b.a_1,4);if(a===0){break a}this.C=this._;switch(a){case 0:break a;case 1:if(!c(this,'i')){return false}break;case 2:if(!c(this,'u')){return false}break;case 3:if(!c(this,'y')){return false}break;case 4:if(this._>=this.A){break a}this._++;break}continue b}this._=e;break b}return true};b.prototype.r_postlude=b.prototype.V;function J(a){var d;var f;var e;b:while(true){f=a._;e=true;a:while(e===true){e=false;a.D=a._;d=n(a,b.a_1,4);if(d===0){break a}a.C=a._;switch(d){case 0:break a;case 1:if(!c(a,'i')){return false}break;case 2:if(!c(a,'u')){return false}break;case 3:if(!c(a,'y')){return false}break;case 4:if(a._>=a.A){break a}a._++;break}continue b}a._=f;break b}return true};b.prototype.S=function(){return!(this.I_pV<=this._)?false:true};b.prototype.r_RV=b.prototype.S;b.prototype.Q=function(){return!(this.I_p1<=this._)?false:true};b.prototype.r_R1=b.prototype.Q;b.prototype.R=function(){return!(this.I_p2<=this._)?false:true};b.prototype.r_R2=b.prototype.R;b.prototype.Y=function(){var a;var E;var H;var e;var D;var g;var F;var G;var h;var I;var A;var B;var p;var k;var l;var m;var n;var o;var i;var q;var s;var t;var u;var v;var w;var x;var y;var z;var J;var K;var L;var C;this.C=this._;a=f(this,b.a_4,43);if(a===0){return false}this.D=this._;switch(a){case 0:return false;case 1:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}break;case 2:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}E=this.A-this._;p=true;c:while(p===true){p=false;this.C=this._;if(!d(this,2,'ic')){this._=this.A-E;break c}this.D=this._;k=true;b:while(k===true){k=false;H=this.A-this._;l=true;a:while(l===true){l=false;if(!(!(this.I_p2<=this._)?false:true)){break a}if(!c(this,'')){return false}break b}this._=this.A-H;if(!c(this,'iqU')){return false}}}break;case 3:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'log')){return false}break;case 4:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'u')){return false}break;case 5:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'ent')){return false}break;case 6:if(!(!(this.I_pV<=this._)?false:true)){return false}if(!c(this,'')){return false}e=this.A-this._;m=true;a:while(m===true){m=false;this.C=this._;a=f(this,b.a_2,6);if(a===0){this._=this.A-e;break a}this.D=this._;switch(a){case 0:this._=this.A-e;break a;case 1:if(!(!(this.I_p2<=this._)?false:true)){this._=this.A-e;break a}if(!c(this,'')){return false}this.C=this._;if(!d(this,2,'at')){this._=this.A-e;break a}this.D=J=this._;if(!(!(this.I_p2<=J)?false:true)){this._=this.A-e;break a}if(!c(this,'')){return false}break;case 2:n=true;b:while(n===true){n=false;D=this.A-this._;o=true;c:while(o===true){o=false;if(!(!(this.I_p2<=this._)?false:true)){break c}if(!c(this,'')){return false}break b}K=this._=this.A-D;if(!(!(this.I_p1<=K)?false:true)){this._=this.A-e;break a}if(!c(this,'eux')){return false}}break;case 3:if(!(!(this.I_p2<=this._)?false:true)){this._=this.A-e;break a}if(!c(this,'')){return false}break;case 4:if(!(!(this.I_pV<=this._)?false:true)){this._=this.A-e;break a}if(!c(this,'i')){return false}break}}break;case 7:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}g=this.A-this._;i=true;a:while(i===true){i=false;this.C=this._;a=f(this,b.a_3,3);if(a===0){this._=this.A-g;break a}this.D=this._;switch(a){case 0:this._=this.A-g;break a;case 1:q=true;c:while(q===true){q=false;F=this.A-this._;s=true;b:while(s===true){s=false;if(!(!(this.I_p2<=this._)?false:true)){break b}if(!c(this,'')){return false}break c}this._=this.A-F;if(!c(this,'abl')){return false}}break;case 2:t=true;b:while(t===true){t=false;G=this.A-this._;u=true;c:while(u===true){u=false;if(!(!(this.I_p2<=this._)?false:true)){break c}if(!c(this,'')){return false}break b}this._=this.A-G;if(!c(this,'iqU')){return false}}break;case 3:if(!(!(this.I_p2<=this._)?false:true)){this._=this.A-g;break a}if(!c(this,'')){return false}break}}break;case 8:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}h=this.A-this._;v=true;a:while(v===true){v=false;this.C=this._;if(!d(this,2,'at')){this._=this.A-h;break a}this.D=L=this._;if(!(!(this.I_p2<=L)?false:true)){this._=this.A-h;break a}if(!c(this,'')){return false}this.C=this._;if(!d(this,2,'ic')){this._=this.A-h;break a}this.D=this._;w=true;b:while(w===true){w=false;I=this.A-this._;x=true;c:while(x===true){x=false;if(!(!(this.I_p2<=this._)?false:true)){break c}if(!c(this,'')){return false}break b}this._=this.A-I;if(!c(this,'iqU')){return false}}}break;case 9:if(!c(this,'eau')){return false}break;case 10:if(!(!(this.I_p1<=this._)?false:true)){return false}if(!c(this,'al')){return false}break;case 11:y=true;a:while(y===true){y=false;A=this.A-this._;z=true;b:while(z===true){z=false;if(!(!(this.I_p2<=this._)?false:true)){break b}if(!c(this,'')){return false}break a}C=this._=this.A-A;if(!(!(this.I_p1<=C)?false:true)){return false}if(!c(this,'eux')){return false}}break;case 12:if(!(!(this.I_p1<=this._)?false:true)){return false}if(!j(this,b.g_v,97,251)){return false}if(!c(this,'')){return false}break;case 13:if(!(!(this.I_pV<=this._)?false:true)){return false}if(!c(this,'ant')){return false}return false;case 14:if(!(!(this.I_pV<=this._)?false:true)){return false}if(!c(this,'ent')){return false}return false;case 15:B=this.A-this._;if(!r(this,b.g_v,97,251)){return false}if(!(!(this.I_pV<=this._)?false:true)){return false}this._=this.A-B;if(!c(this,'')){return false}return false}return true};b.prototype.r_standard_suffix=b.prototype.Y;function K(a){var g;var F;var I;var e;var E;var h;var G;var H;var i;var J;var B;var C;var p;var l;var m;var n;var o;var k;var q;var s;var t;var u;var v;var w;var x;var y;var z;var A;var K;var L;var M;var D;a.C=a._;g=f(a,b.a_4,43);if(g===0){return false}a.D=a._;switch(g){case 0:return false;case 1:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}break;case 2:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}F=a.A-a._;p=true;c:while(p===true){p=false;a.C=a._;if(!d(a,2,'ic')){a._=a.A-F;break c}a.D=a._;l=true;b:while(l===true){l=false;I=a.A-a._;m=true;a:while(m===true){m=false;if(!(!(a.I_p2<=a._)?false:true)){break a}if(!c(a,'')){return false}break b}a._=a.A-I;if(!c(a,'iqU')){return false}}}break;case 3:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'log')){return false}break;case 4:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'u')){return false}break;case 5:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'ent')){return false}break;case 6:if(!(!(a.I_pV<=a._)?false:true)){return false}if(!c(a,'')){return false}e=a.A-a._;n=true;a:while(n===true){n=false;a.C=a._;g=f(a,b.a_2,6);if(g===0){a._=a.A-e;break a}a.D=a._;switch(g){case 0:a._=a.A-e;break a;case 1:if(!(!(a.I_p2<=a._)?false:true)){a._=a.A-e;break a}if(!c(a,'')){return false}a.C=a._;if(!d(a,2,'at')){a._=a.A-e;break a}a.D=K=a._;if(!(!(a.I_p2<=K)?false:true)){a._=a.A-e;break a}if(!c(a,'')){return false}break;case 2:o=true;b:while(o===true){o=false;E=a.A-a._;k=true;c:while(k===true){k=false;if(!(!(a.I_p2<=a._)?false:true)){break c}if(!c(a,'')){return false}break b}L=a._=a.A-E;if(!(!(a.I_p1<=L)?false:true)){a._=a.A-e;break a}if(!c(a,'eux')){return false}}break;case 3:if(!(!(a.I_p2<=a._)?false:true)){a._=a.A-e;break a}if(!c(a,'')){return false}break;case 4:if(!(!(a.I_pV<=a._)?false:true)){a._=a.A-e;break a}if(!c(a,'i')){return false}break}}break;case 7:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}h=a.A-a._;q=true;a:while(q===true){q=false;a.C=a._;g=f(a,b.a_3,3);if(g===0){a._=a.A-h;break a}a.D=a._;switch(g){case 0:a._=a.A-h;break a;case 1:s=true;c:while(s===true){s=false;G=a.A-a._;t=true;b:while(t===true){t=false;if(!(!(a.I_p2<=a._)?false:true)){break b}if(!c(a,'')){return false}break c}a._=a.A-G;if(!c(a,'abl')){return false}}break;case 2:u=true;b:while(u===true){u=false;H=a.A-a._;v=true;c:while(v===true){v=false;if(!(!(a.I_p2<=a._)?false:true)){break c}if(!c(a,'')){return false}break b}a._=a.A-H;if(!c(a,'iqU')){return false}}break;case 3:if(!(!(a.I_p2<=a._)?false:true)){a._=a.A-h;break a}if(!c(a,'')){return false}break}}break;case 8:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}i=a.A-a._;w=true;a:while(w===true){w=false;a.C=a._;if(!d(a,2,'at')){a._=a.A-i;break a}a.D=M=a._;if(!(!(a.I_p2<=M)?false:true)){a._=a.A-i;break a}if(!c(a,'')){return false}a.C=a._;if(!d(a,2,'ic')){a._=a.A-i;break a}a.D=a._;x=true;b:while(x===true){x=false;J=a.A-a._;y=true;c:while(y===true){y=false;if(!(!(a.I_p2<=a._)?false:true)){break c}if(!c(a,'')){return false}break b}a._=a.A-J;if(!c(a,'iqU')){return false}}}break;case 9:if(!c(a,'eau')){return false}break;case 10:if(!(!(a.I_p1<=a._)?false:true)){return false}if(!c(a,'al')){return false}break;case 11:z=true;a:while(z===true){z=false;B=a.A-a._;A=true;b:while(A===true){A=false;if(!(!(a.I_p2<=a._)?false:true)){break b}if(!c(a,'')){return false}break a}D=a._=a.A-B;if(!(!(a.I_p1<=D)?false:true)){return false}if(!c(a,'eux')){return false}}break;case 12:if(!(!(a.I_p1<=a._)?false:true)){return false}if(!j(a,b.g_v,97,251)){return false}if(!c(a,'')){return false}break;case 13:if(!(!(a.I_pV<=a._)?false:true)){return false}if(!c(a,'ant')){return false}return false;case 14:if(!(!(a.I_pV<=a._)?false:true)){return false}if(!c(a,'ent')){return false}return false;case 15:C=a.A-a._;if(!r(a,b.g_v,97,251)){return false}if(!(!(a.I_pV<=a._)?false:true)){return false}a._=a.A-C;if(!c(a,'')){return false}return false}return true};b.prototype.T=function(){var d;var e;var a;var g;var h;var i;e=this.A-(g=this._);if(g<this.I_pV){return false}h=this._=this.I_pV;a=this.B;this.B=h;i=this._=this.A-e;this.C=i;d=f(this,b.a_5,35);if(d===0){this.B=a;return false}this.D=this._;switch(d){case 0:this.B=a;return false;case 1:if(!j(this,b.g_v,97,251)){this.B=a;return false}if(!c(this,'')){return false}break}this.B=a;return true};b.prototype.r_i_verb_suffix=b.prototype.T;function L(a){var e;var g;var d;var h;var i;var k;g=a.A-(h=a._);if(h<a.I_pV){return false}i=a._=a.I_pV;d=a.B;a.B=i;k=a._=a.A-g;a.C=k;e=f(a,b.a_5,35);if(e===0){a.B=d;return false}a.D=a._;switch(e){case 0:a.B=d;return false;case 1:if(!j(a,b.g_v,97,251)){a.B=d;return false}if(!c(a,'')){return false}break}a.B=d;return true};b.prototype.b=function(){var e;var h;var a;var i;var g;var j;var k;var l;h=this.A-(j=this._);if(j<this.I_pV){return false}k=this._=this.I_pV;a=this.B;this.B=k;l=this._=this.A-h;this.C=l;e=f(this,b.a_6,38);if(e===0){this.B=a;return false}this.D=this._;switch(e){case 0:this.B=a;return false;case 1:if(!(!(this.I_p2<=this._)?false:true)){this.B=a;return false}if(!c(this,'')){return false}break;case 2:if(!c(this,'')){return false}break;case 3:if(!c(this,'')){return false}i=this.A-this._;g=true;a:while(g===true){g=false;this.C=this._;if(!d(this,1,'e')){this._=this.A-i;break a}this.D=this._;if(!c(this,'')){return false}}break}this.B=a;return true};b.prototype.r_verb_suffix=b.prototype.b;function M(a){var g;var i;var e;var j;var h;var k;var l;var m;i=a.A-(k=a._);if(k<a.I_pV){return false}l=a._=a.I_pV;e=a.B;a.B=l;m=a._=a.A-i;a.C=m;g=f(a,b.a_6,38);if(g===0){a.B=e;return false}a.D=a._;switch(g){case 0:a.B=e;return false;case 1:if(!(!(a.I_p2<=a._)?false:true)){a.B=e;return false}if(!c(a,'')){return false}break;case 2:if(!c(a,'')){return false}break;case 3:if(!c(a,'')){return false}j=a.A-a._;h=true;a:while(h===true){h=false;a.C=a._;if(!d(a,1,'e')){a._=a.A-j;break a}a.D=a._;if(!c(a,'')){return false}}break}a.B=e;return true};b.prototype.X=function(){var h;var g;var m;var n;var a;var l;var e;var i;var k;var p;var q;var r;var o;g=this.A-this._;e=true;a:while(e===true){e=false;this.C=this._;if(!d(this,1,'s')){this._=this.A-g;break a}this.D=p=this._;m=this.A-p;if(!j(this,b.g_keep_with_s,97,232)){this._=this.A-g;break a}this._=this.A-m;if(!c(this,'')){return false}}n=this.A-(q=this._);if(q<this.I_pV){return false}r=this._=this.I_pV;a=this.B;this.B=r;o=this._=this.A-n;this.C=o;h=f(this,b.a_7,7);if(h===0){this.B=a;return false}this.D=this._;switch(h){case 0:this.B=a;return false;case 1:if(!(!(this.I_p2<=this._)?false:true)){this.B=a;return false}i=true;a:while(i===true){i=false;l=this.A-this._;k=true;b:while(k===true){k=false;if(!d(this,1,'s')){break b}break a}this._=this.A-l;if(!d(this,1,'t')){this.B=a;return false}}if(!c(this,'')){return false}break;case 2:if(!c(this,'i')){return false}break;case 3:if(!c(this,'')){return false}break;case 4:if(!d(this,2,'gu')){this.B=a;return false}if(!c(this,'')){return false}break}this.B=a;return true};b.prototype.r_residual_suffix=b.prototype.X;function w(a){var g;var h;var p;var n;var e;var m;var i;var k;var l;var q;var r;var s;var o;h=a.A-a._;i=true;a:while(i===true){i=false;a.C=a._;if(!d(a,1,'s')){a._=a.A-h;break a}a.D=q=a._;p=a.A-q;if(!j(a,b.g_keep_with_s,97,232)){a._=a.A-h;break a}a._=a.A-p;if(!c(a,'')){return false}}n=a.A-(r=a._);if(r<a.I_pV){return false}s=a._=a.I_pV;e=a.B;a.B=s;o=a._=a.A-n;a.C=o;g=f(a,b.a_7,7);if(g===0){a.B=e;return false}a.D=a._;switch(g){case 0:a.B=e;return false;case 1:if(!(!(a.I_p2<=a._)?false:true)){a.B=e;return false}k=true;a:while(k===true){k=false;m=a.A-a._;l=true;b:while(l===true){l=false;if(!d(a,1,'s')){break b}break a}a._=a.A-m;if(!d(a,1,'t')){a.B=e;return false}}if(!c(a,'')){return false}break;case 2:if(!c(a,'i')){return false}break;case 3:if(!c(a,'')){return false}break;case 4:if(!d(a,2,'gu')){a.B=e;return false}if(!c(a,'')){return false}break}a.B=e;return true};b.prototype.a=function(){var d;var a;d=this.A-this._;if(f(this,b.a_8,5)===0){return false}a=this._=this.A-d;this.C=a;if(a<=this.B){return false}this._--;this.D=this._;return!c(this,'')?false:true};b.prototype.r_un_double=b.prototype.a;function t(a){var e;var d;e=a.A-a._;if(f(a,b.a_8,5)===0){return false}d=a._=a.A-e;a.C=d;if(d<=a.B){return false}a._--;a.D=a._;return!c(a,'')?false:true};b.prototype.Z=function(){var h;var a;var e;var f;var g;a=1;a:while(true){e=true;b:while(e===true){e=false;if(!j(this,b.g_v,97,251)){break b}a--;continue a}break a}if(a>0){return false}this.C=this._;f=true;a:while(f===true){f=false;h=this.A-this._;g=true;b:while(g===true){g=false;if(!d(this,1,'é')){break b}break a}this._=this.A-h;if(!d(this,1,'è')){return false}}this.D=this._;return!c(this,'e')?false:true};b.prototype.r_un_accent=b.prototype.Z;function F(a){var i;var e;var f;var g;var h;e=1;a:while(true){f=true;b:while(f===true){f=false;if(!j(a,b.g_v,97,251)){break b}e--;continue a}break a}if(e>0){return false}a.C=a._;g=true;a:while(g===true){g=false;i=a.A-a._;h=true;b:while(h===true){h=false;if(!d(a,1,'é')){break b}break a}a._=a.A-i;if(!d(a,1,'è')){return false}}a.D=a._;return!c(a,'e')?false:true};b.prototype.J=function(){var u;var z;var A;var B;var C;var j;var s;var v;var x;var y;var e;var f;var g;var h;var i;var a;var b;var k;var l;var m;var n;var o;var p;var q;var D;var E;var G;var N;var O;var P;var Q;var R;var r;u=this._;e=true;a:while(e===true){e=false;if(!H(this)){break a}}D=this._=u;z=D;f=true;a:while(f===true){f=false;if(!I(this)){break a}}N=this._=z;this.B=N;P=this._=O=this.A;A=O-P;g=true;c:while(g===true){g=false;h=true;d:while(h===true){h=false;B=this.A-this._;i=true;e:while(i===true){i=false;C=this.A-this._;a=true;a:while(a===true){a=false;j=this.A-this._;b=true;b:while(b===true){b=false;if(!K(this)){break b}break a}this._=this.A-j;k=true;b:while(k===true){k=false;if(!L(this)){break b}break a}this._=this.A-j;if(!M(this)){break e}}G=this._=(E=this.A)-C;s=E-G;l=true;a:while(l===true){l=false;this.C=this._;m=true;b:while(m===true){m=false;v=this.A-this._;n=true;f:while(n===true){n=false;if(!d(this,1,'Y')){break f}this.D=this._;if(!c(this,'i')){return false}break b}this._=this.A-v;if(!d(this,1,'ç')){this._=this.A-s;break a}this.D=this._;if(!c(this,'c')){return false}}}break d}this._=this.A-B;if(!w(this)){break c}}}R=this._=(Q=this.A)-A;x=Q-R;o=true;a:while(o===true){o=false;if(!t(this)){break a}}this._=this.A-x;p=true;a:while(p===true){p=false;if(!F(this)){break a}}r=this._=this.B;y=r;q=true;a:while(q===true){q=false;if(!J(this)){break a}}this._=y;return true};b.prototype.stem=b.prototype.J;b.prototype.N=function(a){return a instanceof b};b.prototype.equals=b.prototype.N;b.prototype.O=function(){var c;var a;var b;var d;c='FrenchStemmer';a=0;for(b=0;b<c.length;b++){d=c.charCodeAt(b);a=(a<<5)-a+d;a=a&a}return a|0};b.prototype.hashCode=b.prototype.O;b.serialVersionUID=1;g(b,'methodObject',function(){return new b});g(b,'a_0',function(){return[new a('col',-1,-1),new a('par',-1,-1),new a('tap',-1,-1)]});g(b,'a_1',function(){return[new a('',-1,4),new a('I',0,1),new a('U',0,2),new a('Y',0,3)]});g(b,'a_2',function(){return[new a('iqU',-1,3),new a('abl',-1,3),new a('Ièr',-1,4),new a('ièr',-1,4),new a('eus',-1,2),new a('iv',-1,1)]});g(b,'a_3',function(){return[new a('ic',-1,2),new a('abil',-1,1),new a('iv',-1,3)]});g(b,'a_4',function(){return[new a('iqUe',-1,1),new a('atrice',-1,2),new a('ance',-1,1),new a('ence',-1,5),new a('logie',-1,3),new a('able',-1,1),new a('isme',-1,1),new a('euse',-1,11),new a('iste',-1,1),new a('ive',-1,8),new a('if',-1,8),new a('usion',-1,4),new a('ation',-1,2),new a('ution',-1,4),new a('ateur',-1,2),new a('iqUes',-1,1),new a('atrices',-1,2),new a('ances',-1,1),new a('ences',-1,5),new a('logies',-1,3),new a('ables',-1,1),new a('ismes',-1,1),new a('euses',-1,11),new a('istes',-1,1),new a('ives',-1,8),new a('ifs',-1,8),new a('usions',-1,4),new a('ations',-1,2),new a('utions',-1,4),new a('ateurs',-1,2),new a('ments',-1,15),new a('ements',30,6),new a('issements',31,12),new a('ités',-1,7),new a('ment',-1,15),new a('ement',34,6),new a('issement',35,12),new a('amment',34,13),new a('emment',34,14),new a('aux',-1,10),new a('eaux',39,9),new a('eux',-1,1),new a('ité',-1,7)]});g(b,'a_5',function(){return[new a('ira',-1,1),new a('ie',-1,1),new a('isse',-1,1),new a('issante',-1,1),new a('i',-1,1),new a('irai',4,1),new a('ir',-1,1),new a('iras',-1,1),new a('ies',-1,1),new a('îmes',-1,1),new a('isses',-1,1),new a('issantes',-1,1),new a('îtes',-1,1),new a('is',-1,1),new a('irais',13,1),new a('issais',13,1),new a('irions',-1,1),new a('issions',-1,1),new a('irons',-1,1),new a('issons',-1,1),new a('issants',-1,1),new a('it',-1,1),new a('irait',21,1),new a('issait',21,1),new a('issant',-1,1),new a('iraIent',-1,1),new a('issaIent',-1,1),new a('irent',-1,1),new a('issent',-1,1),new a('iront',-1,1),new a('ît',-1,1),new a('iriez',-1,1),new a('issiez',-1,1),new a('irez',-1,1),new a('issez',-1,1)]});g(b,'a_6',function(){return[new a('a',-1,3),new a('era',0,2),new a('asse',-1,3),new a('ante',-1,3),new a('ée',-1,2),new a('ai',-1,3),new a('erai',5,2),new a('er',-1,2),new a('as',-1,3),new a('eras',8,2),new a('âmes',-1,3),new a('asses',-1,3),new a('antes',-1,3),new a('âtes',-1,3),new a('ées',-1,2),new a('ais',-1,3),new a('erais',15,2),new a('ions',-1,1),new a('erions',17,2),new a('assions',17,3),new a('erons',-1,2),new a('ants',-1,3),new a('és',-1,2),new a('ait',-1,3),new a('erait',23,2),new a('ant',-1,3),new a('aIent',-1,3),new a('eraIent',26,2),new a('èrent',-1,2),new a('assent',-1,3),new a('eront',-1,2),new a('ât',-1,3),new a('ez',-1,2),new a('iez',32,2),new a('eriez',33,2),new a('assiez',33,3),new a('erez',32,2),new a('é',-1,2)]});g(b,'a_7',function(){return[new a('e',-1,3),new a('Ière',0,2),new a('ière',0,2),new a('ion',-1,1),new a('Ier',-1,2),new a('ier',-1,2),new a('ë',-1,4)]});g(b,'a_8',function(){return[new a('ell',-1,-1),new a('eill',-1,-1),new a('enn',-1,-1),new a('onn',-1,-1),new a('ett',-1,-1)]});g(b,'g_v',function(){return[17,65,16,1,0,0,0,0,0,0,0,0,0,0,0,128,130,103,8,5]});g(b,'g_keep_with_s',function(){return[1,65,20,0,0,0,0,0,0,0,0,0,0,0,0,0,128]});var q={'src/stemmer.jsx':{Stemmer:p},'src/french-stemmer.jsx':{FrenchStemmer:b}}}(JSX))
var Stemmer = JSX.require("src/french-stemmer.jsx").FrenchStemmer;
"""


class SearchFrench(SearchLanguage):
    lang = 'fr'
    language_name = 'French'
    js_stemmer_rawcode = 'french-stemmer.js'
    js_stemmer_code = js_stemmer
    stopwords = french_stopwords

    def init(self, options):
        # type: (Any) -> None
        self.stemmer = snowballstemmer.stemmer('french')

    def stem(self, word):
        # type: (unicode) -> unicode
        return self.stemmer.stemWord(word.lower())
