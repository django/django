# -*- coding: utf-8 -*-
"""
    sphinx.search.nl
    ~~~~~~~~~~~~~~~~

    Dutch search language: includes the JS porter stemmer.

    :copyright: Copyright 2007-2013 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from sphinx.search import SearchLanguage, parse_stop_word

import snowballstemmer

if False:
    # For type annotation
    from typing import Any  # NOQA


dutch_stopwords = parse_stop_word(u'''
| source: http://snowball.tartarus.org/algorithms/dutch/stop.txt
de             |  the
en             |  and
van            |  of, from
ik             |  I, the ego
te             |  (1) chez, at etc, (2) to, (3) too
dat            |  that, which
die            |  that, those, who, which
in             |  in, inside
een            |  a, an, one
hij            |  he
het            |  the, it
niet           |  not, nothing, naught
zijn           |  (1) to be, being, (2) his, one's, its
is             |  is
was            |  (1) was, past tense of all persons sing. of 'zijn' (to be) (2) wax, (3) the washing, (4) rise of river
op             |  on, upon, at, in, up, used up
aan            |  on, upon, to (as dative)
met            |  with, by
als            |  like, such as, when
voor           |  (1) before, in front of, (2) furrow
had            |  had, past tense all persons sing. of 'hebben' (have)
er             |  there
maar           |  but, only
om             |  round, about, for etc
hem            |  him
dan            |  then
zou            |  should/would, past tense all persons sing. of 'zullen'
of             |  or, whether, if
wat            |  what, something, anything
mijn           |  possessive and noun 'mine'
men            |  people, 'one'
dit            |  this
zo             |  so, thus, in this way
door           |  through by
over           |  over, across
ze             |  she, her, they, them
zich           |  oneself
bij            |  (1) a bee, (2) by, near, at
ook            |  also, too
tot            |  till, until
je             |  you
mij            |  me
uit            |  out of, from
der            |  Old Dutch form of 'van der' still found in surnames
daar           |  (1) there, (2) because
haar           |  (1) her, their, them, (2) hair
naar           |  (1) unpleasant, unwell etc, (2) towards, (3) as
heb            |  present first person sing. of 'to have'
hoe            |  how, why
heeft          |  present third person sing. of 'to have'
hebben         |  'to have' and various parts thereof
deze           |  this
u              |  you
want           |  (1) for, (2) mitten, (3) rigging
nog            |  yet, still
zal            |  'shall', first and third person sing. of verb 'zullen' (will)
me             |  me
zij            |  she, they
nu             |  now
ge             |  'thou', still used in Belgium and south Netherlands
geen           |  none
omdat          |  because
iets           |  something, somewhat
worden         |  to become, grow, get
toch           |  yet, still
al             |  all, every, each
waren          |  (1) 'were' (2) to wander, (3) wares, (3)
veel           |  much, many
meer           |  (1) more, (2) lake
doen           |  to do, to make
toen           |  then, when
moet           |  noun 'spot/mote' and present form of 'to must'
ben            |  (1) am, (2) 'are' in interrogative second person singular of 'to be'
zonder         |  without
kan            |  noun 'can' and present form of 'to be able'
hun            |  their, them
dus            |  so, consequently
alles          |  all, everything, anything
onder          |  under, beneath
ja             |  yes, of course
eens           |  once, one day
hier           |  here
wie            |  who
werd           |  imperfect third person sing. of 'become'
altijd         |  always
doch           |  yet, but etc
wordt          |  present third person sing. of 'become'
wezen          |  (1) to be, (2) 'been' as in 'been fishing', (3) orphans
kunnen         |  to be able
ons            |  us/our
zelf           |  self
tegen          |  against, towards, at
na             |  after, near
reeds          |  already
wil            |  (1) present tense of 'want', (2) 'will', noun, (3) fender
kon            |  could; past tense of 'to be able'
niets          |  nothing
uw             |  your
iemand         |  somebody
geweest        |  been; past participle of 'be'
andere         |  other
''')

js_stemmer = u"""
var JSX={};(function(m){function n(b,e){var a=function(){};a.prototype=e.prototype;var c=new a;for(var d in b){b[d].prototype=c}}function L(c,b){for(var a in b.prototype)if(b.prototype.hasOwnProperty(a))c.prototype[a]=b.prototype[a]}function e(a,b,d){function c(a,b,c){delete a[b];a[b]=c;return c}Object.defineProperty(a,b,{get:function(){return c(a,b,d())},set:function(d){c(a,b,d)},enumerable:true,configurable:true})}function K(a,b,c){return a[b]=a[b]/c|0}var I=parseInt;var E=parseFloat;function M(a){return a!==a}var B=isFinite;var A=encodeURIComponent;var z=decodeURIComponent;var y=encodeURI;var x=decodeURI;var w=Object.prototype.toString;var C=Object.prototype.hasOwnProperty;function l(){}m.require=function(b){var a=t[b];return a!==undefined?a:null};m.profilerIsRunning=function(){return l.getResults!=null};m.getProfileResults=function(){return(l.getResults||function(){return{}})()};m.postProfileResults=function(a,b){if(l.postResults==null)throw new Error('profiler has not been turned on');return l.postResults(a,b)};m.resetProfileResults=function(){if(l.resetResults==null)throw new Error('profiler has not been turned on');return l.resetResults()};m.DEBUG=false;function v(){};n([v],Error);function c(a,b,c){this.F=a.length;this.K=a;this.L=b;this.I=c;this.H=null;this.P=null};n([c],Object);function s(){};n([s],Object);function g(){var a;var b;var c;this.G={};a=this.D='';b=this._=0;c=this.A=a.length;this.E=0;this.C=b;this.B=c};n([g],s);function D(a,b){a.D=b.D;a._=b._;a.A=b.A;a.E=b.E;a.C=b.C;a.B=b.B};function i(b,d,c,e){var a;if(b._>=b.A){return false}a=b.D.charCodeAt(b._);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._++;return true};function r(a,d,c,e){var b;if(a._>=a.A){return false}b=a.D.charCodeAt(a._);if(b>e||b<c){a._++;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._++;return true}return false};function f(a,d,c,e){var b;if(a._<=a.E){return false}b=a.D.charCodeAt(a._-1);if(b>e||b<c){a._--;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._--;return true}return false};function k(a,b,d){var c;if(a.A-a._<b){return false}if(a.D.slice(c=a._,c+b)!==d){return false}a._+=b;return true};function d(a,b,d){var c;if(a._-a.E<b){return false}if(a.D.slice((c=a._)-b,c)!==d){return false}a._-=b;return true};function q(f,m,p){var b;var d;var e;var n;var g;var k;var l;var i;var h;var c;var a;var j;var o;b=0;d=p;e=f._;n=f.A;g=0;k=0;l=false;while(true){i=b+(d-b>>>1);h=0;c=g<k?g:k;a=m[i];for(j=c;j<a.F;j++){if(e+c===n){h=-1;break}h=f.D.charCodeAt(e+c)-a.K.charCodeAt(j);if(h!==0){break}c++}if(h<0){d=i;k=c}else{b=i;g=c}if(d-b<=1){if(b>0){break}if(d===b){break}if(l){break}l=true}}while(true){a=m[b];if(g>=a.F){f._=e+a.F|0;if(a.H==null){return a.I}o=a.H(a.P);f._=e+a.F|0;if(o){return a.I}}b=a.L;if(b<0){return 0}}return-1};function h(d,m,p){var b;var g;var e;var n;var f;var k;var l;var i;var h;var c;var a;var j;var o;b=0;g=p;e=d._;n=d.E;f=0;k=0;l=false;while(true){i=b+(g-b>>1);h=0;c=f<k?f:k;a=m[i];for(j=a.F-1-c;j>=0;j--){if(e-c===n){h=-1;break}h=d.D.charCodeAt(e-1-c)-a.K.charCodeAt(j);if(h!==0){break}c++}if(h<0){g=i;k=c}else{b=i;f=c}if(g-b<=1){if(b>0){break}if(g===b){break}if(l){break}l=true}}while(true){a=m[b];if(f>=a.F){d._=e-a.F|0;if(a.H==null){return a.I}o=a.H(d);d._=e-a.F|0;if(o){return a.I}}b=a.L;if(b<0){return 0}}return-1};function u(a,b,d,e){var c;c=e.length-(d-b);a.D=a.D.slice(0,b)+e+a.D.slice(d);a.A+=c|0;if(a._>=d){a._+=c|0}else if(a._>b){a._=b}return c|0};function b(a,f){var b;var c;var d;var e;b=false;if((c=a.C)<0||c>(d=a.B)||d>(e=a.A)||e>a.D.length?false:true){u(a,a.C,a.B,f);b=true}return b};g.prototype.J=function(){return false};g.prototype.Z=function(b){var a;var c;var d;var e;a=this.G['.'+b];if(a==null){c=this.D=b;d=this._=0;e=this.A=c.length;this.E=0;this.C=d;this.B=e;this.J();a=this.D;this.G['.'+b]=a}return a};g.prototype.stemWord=g.prototype.Z;g.prototype.a=function(e){var d;var b;var c;var a;var f;var g;var h;d=[];for(b=0;b<e.length;b++){c=e[b];a=this.G['.'+c];if(a==null){f=this.D=c;g=this._=0;h=this.A=f.length;this.E=0;this.C=g;this.B=h;this.J();a=this.D;this.G['.'+c]=a}d.push(a)}return d};g.prototype.stemWords=g.prototype.a;function a(){g.call(this);this.I_p2=0;this.I_p1=0;this.B_e_found=false};n([a],g);a.prototype.M=function(a){this.I_p2=a.I_p2;this.I_p1=a.I_p1;this.B_e_found=a.B_e_found;D(this,a)};a.prototype.copy_from=a.prototype.M;a.prototype.W=function(){var e;var m;var n;var o;var p;var d;var s;var c;var f;var g;var h;var j;var l;var t;var r;m=this._;b:while(true){n=this._;c=true;a:while(c===true){c=false;this.C=this._;e=q(this,a.a_0,11);if(e===0){break a}this.B=this._;switch(e){case 0:break a;case 1:if(!b(this,'a')){return false}break;case 2:if(!b(this,'e')){return false}break;case 3:if(!b(this,'i')){return false}break;case 4:if(!b(this,'o')){return false}break;case 5:if(!b(this,'u')){return false}break;case 6:if(this._>=this.A){break a}this._++;break}continue b}this._=n;break b}t=this._=m;o=t;f=true;a:while(f===true){f=false;this.C=this._;if(!k(this,1,'y')){this._=o;break a}this.B=this._;if(!b(this,'Y')){return false}}a:while(true){p=this._;g=true;d:while(g===true){g=false;e:while(true){d=this._;h=true;b:while(h===true){h=false;if(!i(this,a.g_v,97,232)){break b}this.C=this._;j=true;f:while(j===true){j=false;s=this._;l=true;c:while(l===true){l=false;if(!k(this,1,'i')){break c}this.B=this._;if(!i(this,a.g_v,97,232)){break c}if(!b(this,'I')){return false}break f}this._=s;if(!k(this,1,'y')){break b}this.B=this._;if(!b(this,'Y')){return false}}this._=d;break e}r=this._=d;if(r>=this.A){break d}this._++}continue a}this._=p;break a}return true};a.prototype.r_prelude=a.prototype.W;function F(c){var d;var s;var t;var o;var p;var e;var n;var f;var g;var h;var j;var l;var m;var u;var r;s=c._;b:while(true){t=c._;f=true;a:while(f===true){f=false;c.C=c._;d=q(c,a.a_0,11);if(d===0){break a}c.B=c._;switch(d){case 0:break a;case 1:if(!b(c,'a')){return false}break;case 2:if(!b(c,'e')){return false}break;case 3:if(!b(c,'i')){return false}break;case 4:if(!b(c,'o')){return false}break;case 5:if(!b(c,'u')){return false}break;case 6:if(c._>=c.A){break a}c._++;break}continue b}c._=t;break b}u=c._=s;o=u;g=true;a:while(g===true){g=false;c.C=c._;if(!k(c,1,'y')){c._=o;break a}c.B=c._;if(!b(c,'Y')){return false}}a:while(true){p=c._;h=true;d:while(h===true){h=false;e:while(true){e=c._;j=true;b:while(j===true){j=false;if(!i(c,a.g_v,97,232)){break b}c.C=c._;l=true;f:while(l===true){l=false;n=c._;m=true;c:while(m===true){m=false;if(!k(c,1,'i')){break c}c.B=c._;if(!i(c,a.g_v,97,232)){break c}if(!b(c,'I')){return false}break f}c._=n;if(!k(c,1,'y')){break b}c.B=c._;if(!b(c,'Y')){return false}}c._=e;break e}r=c._=e;if(r>=c.A){break d}c._++}continue a}c._=p;break a}return true};a.prototype.U=function(){var b;var c;var d;var e;var f;var g;this.I_p1=g=this.A;this.I_p2=g;a:while(true){b=true;b:while(b===true){b=false;if(!i(this,a.g_v,97,232)){break b}break a}if(this._>=this.A){return false}this._++}a:while(true){c=true;b:while(c===true){c=false;if(!r(this,a.g_v,97,232)){break b}break a}if(this._>=this.A){return false}this._++}this.I_p1=this._;d=true;a:while(d===true){d=false;if(!(this.I_p1<3)){break a}this.I_p1=3}a:while(true){e=true;b:while(e===true){e=false;if(!i(this,a.g_v,97,232)){break b}break a}if(this._>=this.A){return false}this._++}a:while(true){f=true;b:while(f===true){f=false;if(!r(this,a.g_v,97,232)){break b}break a}if(this._>=this.A){return false}this._++}this.I_p2=this._;return true};a.prototype.r_mark_regions=a.prototype.U;function G(b){var c;var d;var e;var f;var g;var h;b.I_p1=h=b.A;b.I_p2=h;a:while(true){c=true;b:while(c===true){c=false;if(!i(b,a.g_v,97,232)){break b}break a}if(b._>=b.A){return false}b._++}a:while(true){d=true;b:while(d===true){d=false;if(!r(b,a.g_v,97,232)){break b}break a}if(b._>=b.A){return false}b._++}b.I_p1=b._;e=true;a:while(e===true){e=false;if(!(b.I_p1<3)){break a}b.I_p1=3}a:while(true){f=true;b:while(f===true){f=false;if(!i(b,a.g_v,97,232)){break b}break a}if(b._>=b.A){return false}b._++}a:while(true){g=true;b:while(g===true){g=false;if(!r(b,a.g_v,97,232)){break b}break a}if(b._>=b.A){return false}b._++}b.I_p2=b._;return true};a.prototype.V=function(){var c;var e;var d;b:while(true){e=this._;d=true;a:while(d===true){d=false;this.C=this._;c=q(this,a.a_1,3);if(c===0){break a}this.B=this._;switch(c){case 0:break a;case 1:if(!b(this,'y')){return false}break;case 2:if(!b(this,'i')){return false}break;case 3:if(this._>=this.A){break a}this._++;break}continue b}this._=e;break b}return true};a.prototype.r_postlude=a.prototype.V;function H(c){var d;var f;var e;b:while(true){f=c._;e=true;a:while(e===true){e=false;c.C=c._;d=q(c,a.a_1,3);if(d===0){break a}c.B=c._;switch(d){case 0:break a;case 1:if(!b(c,'y')){return false}break;case 2:if(!b(c,'i')){return false}break;case 3:if(c._>=c.A){break a}c._++;break}continue b}c._=f;break b}return true};a.prototype.Q=function(){return!(this.I_p1<=this._)?false:true};a.prototype.r_R1=a.prototype.Q;a.prototype.R=function(){return!(this.I_p2<=this._)?false:true};a.prototype.r_R2=a.prototype.R;a.prototype.Y=function(){var d;var c;d=this.A-this._;if(h(this,a.a_2,3)===0){return false}c=this._=this.A-d;this.B=c;if(c<=this.E){return false}this._--;this.C=this._;return!b(this,'')?false:true};a.prototype.r_undouble=a.prototype.Y;function j(c){var e;var d;e=c.A-c._;if(h(c,a.a_2,3)===0){return false}d=c._=c.A-e;c.B=d;if(d<=c.E){return false}c._--;c.C=c._;return!b(c,'')?false:true};a.prototype.S=function(){var c;var e;this.B_e_found=false;this.B=this._;if(!d(this,1,'e')){return false}this.C=e=this._;if(!(!(this.I_p1<=e)?false:true)){return false}c=this.A-this._;if(!f(this,a.g_v,97,232)){return false}this._=this.A-c;if(!b(this,'')){return false}this.B_e_found=true;return!j(this)?false:true};a.prototype.r_e_ending=a.prototype.S;function o(c){var e;var g;c.B_e_found=false;c.B=c._;if(!d(c,1,'e')){return false}c.C=g=c._;if(!(!(c.I_p1<=g)?false:true)){return false}e=c.A-c._;if(!f(c,a.g_v,97,232)){return false}c._=c.A-e;if(!b(c,'')){return false}c.B_e_found=true;return!j(c)?false:true};a.prototype.T=function(){var e;var g;var c;var h;var i;if(!(!(this.I_p1<=this._)?false:true)){return false}e=this.A-this._;if(!f(this,a.g_v,97,232)){return false}i=this._=(h=this.A)-e;g=h-i;c=true;a:while(c===true){c=false;if(!d(this,3,'gem')){break a}return false}this._=this.A-g;return!b(this,'')?false:!j(this)?false:true};a.prototype.r_en_ending=a.prototype.T;function p(c){var g;var h;var e;var i;var k;if(!(!(c.I_p1<=c._)?false:true)){return false}g=c.A-c._;if(!f(c,a.g_v,97,232)){return false}k=c._=(i=c.A)-g;h=i-k;e=true;a:while(e===true){e=false;if(!d(c,3,'gem')){break a}return false}c._=c.A-h;return!b(c,'')?false:!j(c)?false:true};a.prototype.X=function(){var c;var v;var w;var x;var y;var z;var A;var B;var C;var D;var M;var m;var g;var i;var k;var l;var e;var n;var q;var r;var s;var E;var F;var G;var H;var I;var J;var K;var L;var t;var N;var u;v=this.A-this._;m=true;a:while(m===true){m=false;this.B=this._;c=h(this,a.a_3,5);if(c===0){break a}this.C=this._;switch(c){case 0:break a;case 1:if(!(!(this.I_p1<=this._)?false:true)){break a}if(!b(this,'heid')){return false}break;case 2:if(!p(this)){break a}break;case 3:if(!(!(this.I_p1<=this._)?false:true)){break a}if(!f(this,a.g_v_j,97,232)){break a}if(!b(this,'')){return false}break}}F=this._=(E=this.A)-v;w=E-F;g=true;a:while(g===true){g=false;if(!o(this)){break a}}I=this._=(H=this.A)-w;x=H-I;i=true;a:while(i===true){i=false;this.B=this._;if(!d(this,4,'heid')){break a}this.C=G=this._;if(!(!(this.I_p2<=G)?false:true)){break a}y=this.A-this._;k=true;b:while(k===true){k=false;if(!d(this,1,'c')){break b}break a}this._=this.A-y;if(!b(this,'')){return false}this.B=this._;if(!d(this,2,'en')){break a}this.C=this._;if(!p(this)){break a}}L=this._=(K=this.A)-x;z=K-L;l=true;a:while(l===true){l=false;this.B=this._;c=h(this,a.a_4,6);if(c===0){break a}this.C=this._;switch(c){case 0:break a;case 1:if(!(!(this.I_p2<=this._)?false:true)){break a}if(!b(this,'')){return false}e=true;c:while(e===true){e=false;A=this.A-this._;n=true;b:while(n===true){n=false;this.B=this._;if(!d(this,2,'ig')){break b}this.C=J=this._;if(!(!(this.I_p2<=J)?false:true)){break b}B=this.A-this._;q=true;d:while(q===true){q=false;if(!d(this,1,'e')){break d}break b}this._=this.A-B;if(!b(this,'')){return false}break c}this._=this.A-A;if(!j(this)){break a}}break;case 2:if(!(!(this.I_p2<=this._)?false:true)){break a}C=this.A-this._;r=true;b:while(r===true){r=false;if(!d(this,1,'e')){break b}break a}this._=this.A-C;if(!b(this,'')){return false}break;case 3:if(!(!(this.I_p2<=this._)?false:true)){break a}if(!b(this,'')){return false}if(!o(this)){break a}break;case 4:if(!(!(this.I_p2<=this._)?false:true)){break a}if(!b(this,'')){return false}break;case 5:if(!(!(this.I_p2<=this._)?false:true)){break a}if(!this.B_e_found){break a}if(!b(this,'')){return false}break}}u=this._=(N=this.A)-z;D=N-u;s=true;a:while(s===true){s=false;if(!f(this,a.g_v_I,73,232)){break a}M=this.A-this._;if(h(this,a.a_5,4)===0){break a}if(!f(this,a.g_v,97,232)){break a}t=this._=this.A-M;this.B=t;if(t<=this.E){break a}this._--;this.C=this._;if(!b(this,'')){return false}}this._=this.A-D;return true};a.prototype.r_standard_suffix=a.prototype.X;function J(c){var e;var w;var x;var y;var z;var A;var B;var C;var D;var E;var N;var g;var i;var k;var l;var m;var n;var q;var r;var s;var t;var F;var G;var H;var I;var J;var K;var L;var M;var u;var O;var v;w=c.A-c._;g=true;a:while(g===true){g=false;c.B=c._;e=h(c,a.a_3,5);if(e===0){break a}c.C=c._;switch(e){case 0:break a;case 1:if(!(!(c.I_p1<=c._)?false:true)){break a}if(!b(c,'heid')){return false}break;case 2:if(!p(c)){break a}break;case 3:if(!(!(c.I_p1<=c._)?false:true)){break a}if(!f(c,a.g_v_j,97,232)){break a}if(!b(c,'')){return false}break}}G=c._=(F=c.A)-w;x=F-G;i=true;a:while(i===true){i=false;if(!o(c)){break a}}J=c._=(I=c.A)-x;y=I-J;k=true;a:while(k===true){k=false;c.B=c._;if(!d(c,4,'heid')){break a}c.C=H=c._;if(!(!(c.I_p2<=H)?false:true)){break a}z=c.A-c._;l=true;b:while(l===true){l=false;if(!d(c,1,'c')){break b}break a}c._=c.A-z;if(!b(c,'')){return false}c.B=c._;if(!d(c,2,'en')){break a}c.C=c._;if(!p(c)){break a}}M=c._=(L=c.A)-y;A=L-M;m=true;a:while(m===true){m=false;c.B=c._;e=h(c,a.a_4,6);if(e===0){break a}c.C=c._;switch(e){case 0:break a;case 1:if(!(!(c.I_p2<=c._)?false:true)){break a}if(!b(c,'')){return false}n=true;c:while(n===true){n=false;B=c.A-c._;q=true;b:while(q===true){q=false;c.B=c._;if(!d(c,2,'ig')){break b}c.C=K=c._;if(!(!(c.I_p2<=K)?false:true)){break b}C=c.A-c._;r=true;d:while(r===true){r=false;if(!d(c,1,'e')){break d}break b}c._=c.A-C;if(!b(c,'')){return false}break c}c._=c.A-B;if(!j(c)){break a}}break;case 2:if(!(!(c.I_p2<=c._)?false:true)){break a}D=c.A-c._;s=true;b:while(s===true){s=false;if(!d(c,1,'e')){break b}break a}c._=c.A-D;if(!b(c,'')){return false}break;case 3:if(!(!(c.I_p2<=c._)?false:true)){break a}if(!b(c,'')){return false}if(!o(c)){break a}break;case 4:if(!(!(c.I_p2<=c._)?false:true)){break a}if(!b(c,'')){return false}break;case 5:if(!(!(c.I_p2<=c._)?false:true)){break a}if(!c.B_e_found){break a}if(!b(c,'')){return false}break}}v=c._=(O=c.A)-A;E=O-v;t=true;a:while(t===true){t=false;if(!f(c,a.g_v_I,73,232)){break a}N=c.A-c._;if(h(c,a.a_5,4)===0){break a}if(!f(c,a.g_v,97,232)){break a}u=c._=c.A-N;c.B=u;if(u<=c.E){break a}c._--;c.C=c._;if(!b(c,'')){return false}}c._=c.A-E;return true};a.prototype.J=function(){var f;var g;var h;var b;var a;var c;var d;var i;var j;var e;f=this._;b=true;a:while(b===true){b=false;if(!F(this)){break a}}i=this._=f;g=i;a=true;a:while(a===true){a=false;if(!G(this)){break a}}j=this._=g;this.E=j;this._=this.A;c=true;a:while(c===true){c=false;if(!J(this)){break a}}e=this._=this.E;h=e;d=true;a:while(d===true){d=false;if(!H(this)){break a}}this._=h;return true};a.prototype.stem=a.prototype.J;a.prototype.N=function(b){return b instanceof a};a.prototype.equals=a.prototype.N;a.prototype.O=function(){var c;var a;var b;var d;c='DutchStemmer';a=0;for(b=0;b<c.length;b++){d=c.charCodeAt(b);a=(a<<5)-a+d;a=a&a}return a|0};a.prototype.hashCode=a.prototype.O;a.serialVersionUID=1;e(a,'methodObject',function(){return new a});e(a,'a_0',function(){return[new c('',-1,6),new c('á',0,1),new c('ä',0,1),new c('é',0,2),new c('ë',0,2),new c('í',0,3),new c('ï',0,3),new c('ó',0,4),new c('ö',0,4),new c('ú',0,5),new c('ü',0,5)]});e(a,'a_1',function(){return[new c('',-1,3),new c('I',0,2),new c('Y',0,1)]});e(a,'a_2',function(){return[new c('dd',-1,-1),new c('kk',-1,-1),new c('tt',-1,-1)]});e(a,'a_3',function(){return[new c('ene',-1,2),new c('se',-1,3),new c('en',-1,2),new c('heden',2,1),new c('s',-1,3)]});e(a,'a_4',function(){return[new c('end',-1,1),new c('ig',-1,2),new c('ing',-1,1),new c('lijk',-1,3),new c('baar',-1,4),new c('bar',-1,5)]});e(a,'a_5',function(){return[new c('aa',-1,-1),new c('ee',-1,-1),new c('oo',-1,-1),new c('uu',-1,-1)]});e(a,'g_v',function(){return[17,65,16,1,0,0,0,0,0,0,0,0,0,0,0,0,128]});e(a,'g_v_I',function(){return[1,0,0,17,65,16,1,0,0,0,0,0,0,0,0,0,0,0,0,128]});e(a,'g_v_j',function(){return[17,67,16,1,0,0,0,0,0,0,0,0,0,0,0,0,128]});var t={'src/stemmer.jsx':{Stemmer:s},'src/dutch-stemmer.jsx':{DutchStemmer:a}}}(JSX))
var Stemmer = JSX.require("src/dutch-stemmer.jsx").DutchStemmer;
"""


class SearchDutch(SearchLanguage):
    lang = 'nl'
    language_name = 'Dutch'
    js_stemmer_rawcode = 'dutch-stemmer.js'
    js_stemmer_code = js_stemmer
    stopwords = dutch_stopwords

    def init(self, options):
        # type: (Any) -> None
        self.stemmer = snowballstemmer.stemmer('dutch')

    def stem(self, word):
        # type: (unicode) -> unicode
        return self.stemmer.stemWord(word.lower())
