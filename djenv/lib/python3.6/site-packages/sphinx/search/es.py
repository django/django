# -*- coding: utf-8 -*-
"""
    sphinx.search.es
    ~~~~~~~~~~~~~~~~

    Spanish search language: includes the JS Spanish stemmer.

    :copyright: Copyright 2007-2013 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from sphinx.search import SearchLanguage, parse_stop_word

import snowballstemmer

if False:
    # For type annotation
    from typing import Any  # NOQA


spanish_stopwords = parse_stop_word(u'''
|source: http://snowball.tartarus.org/algorithms/spanish/stop.txt
de             |  from, of
la             |  the, her
que            |  who, that
el             |  the
en             |  in
y              |  and
a              |  to
los            |  the, them
del            |  de + el
se             |  himself, from him etc
las            |  the, them
por            |  for, by, etc
un             |  a
para           |  for
con            |  with
no             |  no
una            |  a
su             |  his, her
al             |  a + el
  | es         from SER
lo             |  him
como           |  how
más            |  more
pero           |  pero
sus            |  su plural
le             |  to him, her
ya             |  already
o              |  or
  | fue        from SER
este           |  this
  | ha         from HABER
sí             |  himself etc
porque         |  because
esta           |  this
  | son        from SER
entre          |  between
  | está     from ESTAR
cuando         |  when
muy            |  very
sin            |  without
sobre          |  on
  | ser        from SER
  | tiene      from TENER
también        |  also
me             |  me
hasta          |  until
hay            |  there is/are
donde          |  where
  | han        from HABER
quien          |  whom, that
  | están      from ESTAR
  | estado     from ESTAR
desde          |  from
todo           |  all
nos            |  us
durante        |  during
  | estados    from ESTAR
todos          |  all
uno            |  a
les            |  to them
ni             |  nor
contra         |  against
otros          |  other
  | fueron     from SER
ese            |  that
eso            |  that
  | había      from HABER
ante           |  before
ellos          |  they
e              |  and (variant of y)
esto           |  this
mí             |  me
antes          |  before
algunos        |  some
qué            |  what?
unos           |  a
yo             |  I
otro           |  other
otras          |  other
otra           |  other
él             |  he
tanto          |  so much, many
esa            |  that
estos          |  these
mucho          |  much, many
quienes        |  who
nada           |  nothing
muchos         |  many
cual           |  who
  | sea        from SER
poco           |  few
ella           |  she
estar          |  to be
  | haber      from HABER
estas          |  these
  | estaba     from ESTAR
  | estamos    from ESTAR
algunas        |  some
algo           |  something
nosotros       |  we

      | other forms

mi             |  me
mis            |  mi plural
tú             |  thou
te             |  thee
ti             |  thee
tu             |  thy
tus            |  tu plural
ellas          |  they
nosotras       |  we
vosotros       |  you
vosotras       |  you
os             |  you
mío            |  mine
mía            |
míos           |
mías           |
tuyo           |  thine
tuya           |
tuyos          |
tuyas          |
suyo           |  his, hers, theirs
suya           |
suyos          |
suyas          |
nuestro        |  ours
nuestra        |
nuestros       |
nuestras       |
vuestro        |  yours
vuestra        |
vuestros       |
vuestras       |
esos           |  those
esas           |  those

               | forms of estar, to be (not including the infinitive):
estoy
estás
está
estamos
estáis
están
esté
estés
estemos
estéis
estén
estaré
estarás
estará
estaremos
estaréis
estarán
estaría
estarías
estaríamos
estaríais
estarían
estaba
estabas
estábamos
estabais
estaban
estuve
estuviste
estuvo
estuvimos
estuvisteis
estuvieron
estuviera
estuvieras
estuviéramos
estuvierais
estuvieran
estuviese
estuvieses
estuviésemos
estuvieseis
estuviesen
estando
estado
estada
estados
estadas
estad

               | forms of haber, to have (not including the infinitive):
he
has
ha
hemos
habéis
han
haya
hayas
hayamos
hayáis
hayan
habré
habrás
habrá
habremos
habréis
habrán
habría
habrías
habríamos
habríais
habrían
había
habías
habíamos
habíais
habían
hube
hubiste
hubo
hubimos
hubisteis
hubieron
hubiera
hubieras
hubiéramos
hubierais
hubieran
hubiese
hubieses
hubiésemos
hubieseis
hubiesen
habiendo
habido
habida
habidos
habidas

               | forms of ser, to be (not including the infinitive):
soy
eres
es
somos
sois
son
sea
seas
seamos
seáis
sean
seré
serás
será
seremos
seréis
serán
sería
serías
seríamos
seríais
serían
era
eras
éramos
erais
eran
fui
fuiste
fue
fuimos
fuisteis
fueron
fuera
fueras
fuéramos
fuerais
fueran
fuese
fueses
fuésemos
fueseis
fuesen
siendo
sido
  |  sed also means 'thirst'

               | forms of tener, to have (not including the infinitive):
tengo
tienes
tiene
tenemos
tenéis
tienen
tenga
tengas
tengamos
tengáis
tengan
tendré
tendrás
tendrá
tendremos
tendréis
tendrán
tendría
tendrías
tendríamos
tendríais
tendrían
tenía
tenías
teníamos
teníais
tenían
tuve
tuviste
tuvo
tuvimos
tuvisteis
tuvieron
tuviera
tuvieras
tuviéramos
tuvierais
tuvieran
tuviese
tuvieses
tuviésemos
tuvieseis
tuviesen
teniendo
tenido
tenida
tenidos
tenidas
tened
''')

js_stemmer = u"""
var JSX={};(function(k){function l(b,e){var a=function(){};a.prototype=e.prototype;var c=new a;for(var d in b){b[d].prototype=c}}function I(c,b){for(var a in b.prototype)if(b.prototype.hasOwnProperty(a))c.prototype[a]=b.prototype[a]}function g(a,b,d){function c(a,b,c){delete a[b];a[b]=c;return c}Object.defineProperty(a,b,{get:function(){return c(a,b,d())},set:function(d){c(a,b,d)},enumerable:true,configurable:true})}function J(a,b,c){return a[b]=a[b]/c|0}var p=parseInt;var z=parseFloat;function K(a){return a!==a}var x=isFinite;var w=encodeURIComponent;var u=decodeURIComponent;var t=encodeURI;var s=decodeURI;var A=Object.prototype.toString;var q=Object.prototype.hasOwnProperty;function j(){}k.require=function(b){var a=o[b];return a!==undefined?a:null};k.profilerIsRunning=function(){return j.getResults!=null};k.getProfileResults=function(){return(j.getResults||function(){return{}})()};k.postProfileResults=function(a,b){if(j.postResults==null)throw new Error('profiler has not been turned on');return j.postResults(a,b)};k.resetProfileResults=function(){if(j.resetResults==null)throw new Error('profiler has not been turned on');return j.resetResults()};k.DEBUG=false;function r(){};l([r],Error);function a(a,b,c){this.F=a.length;this.K=a;this.L=b;this.I=c;this.H=null;this.P=null};l([a],Object);function m(){};l([m],Object);function i(){var a;var b;var c;this.G={};a=this.E='';b=this._=0;c=this.A=a.length;this.D=0;this.B=b;this.C=c};l([i],m);function v(a,b){a.E=b.E;a._=b._;a.A=b.A;a.D=b.D;a.B=b.B;a.C=b.C};function f(b,d,c,e){var a;if(b._>=b.A){return false}a=b.E.charCodeAt(b._);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._++;return true};function h(a,d,c,e){var b;if(a._>=a.A){return false}b=a.E.charCodeAt(a._);if(b>e||b<c){a._++;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._++;return true}return false};function d(a,b,d){var c;if(a._-a.D<b){return false}if(a.E.slice((c=a._)-b,c)!==d){return false}a._-=b;return true};function n(f,m,p){var b;var d;var e;var n;var g;var k;var l;var i;var h;var c;var a;var j;var o;b=0;d=p;e=f._;n=f.A;g=0;k=0;l=false;while(true){i=b+(d-b>>>1);h=0;c=g<k?g:k;a=m[i];for(j=c;j<a.F;j++){if(e+c===n){h=-1;break}h=f.E.charCodeAt(e+c)-a.K.charCodeAt(j);if(h!==0){break}c++}if(h<0){d=i;k=c}else{b=i;g=c}if(d-b<=1){if(b>0){break}if(d===b){break}if(l){break}l=true}}while(true){a=m[b];if(g>=a.F){f._=e+a.F|0;if(a.H==null){return a.I}o=a.H(a.P);f._=e+a.F|0;if(o){return a.I}}b=a.L;if(b<0){return 0}}return-1};function e(d,m,p){var b;var g;var e;var n;var f;var k;var l;var i;var h;var c;var a;var j;var o;b=0;g=p;e=d._;n=d.D;f=0;k=0;l=false;while(true){i=b+(g-b>>1);h=0;c=f<k?f:k;a=m[i];for(j=a.F-1-c;j>=0;j--){if(e-c===n){h=-1;break}h=d.E.charCodeAt(e-1-c)-a.K.charCodeAt(j);if(h!==0){break}c++}if(h<0){g=i;k=c}else{b=i;f=c}if(g-b<=1){if(b>0){break}if(g===b){break}if(l){break}l=true}}while(true){a=m[b];if(f>=a.F){d._=e-a.F|0;if(a.H==null){return a.I}o=a.H(d);d._=e-a.F|0;if(o){return a.I}}b=a.L;if(b<0){return 0}}return-1};function B(a,b,d,e){var c;c=e.length-(d-b);a.E=a.E.slice(0,b)+e+a.E.slice(d);a.A+=c|0;if(a._>=d){a._+=c|0}else if(a._>b){a._=b}return c|0};function c(a,f){var b;var c;var d;var e;b=false;if((c=a.B)<0||c>(d=a.C)||d>(e=a.A)||e>a.E.length?false:true){B(a,a.B,a.C,f);b=true}return b};i.prototype.J=function(){return false};i.prototype.a=function(b){var a;var c;var d;var e;a=this.G['.'+b];if(a==null){c=this.E=b;d=this._=0;e=this.A=c.length;this.D=0;this.B=d;this.C=e;this.J();a=this.E;this.G['.'+b]=a}return a};i.prototype.stemWord=i.prototype.a;i.prototype.b=function(e){var d;var b;var c;var a;var f;var g;var h;d=[];for(b=0;b<e.length;b++){c=e[b];a=this.G['.'+c];if(a==null){f=this.E=c;g=this._=0;h=this.A=f.length;this.D=0;this.B=g;this.C=h;this.J();a=this.E;this.G['.'+c]=a}d.push(a)}return d};i.prototype.stemWords=i.prototype.b;function b(){i.call(this);this.I_p2=0;this.I_p1=0;this.I_pV=0};l([b],i);b.prototype.M=function(a){this.I_p2=a.I_p2;this.I_p1=a.I_p1;this.I_pV=a.I_pV;v(this,a)};b.prototype.copy_from=b.prototype.M;b.prototype.U=function(){var u;var w;var x;var y;var t;var l;var d;var e;var g;var i;var c;var j;var k;var a;var m;var n;var o;var p;var q;var r;var s;var v;this.I_pV=s=this.A;this.I_p1=s;this.I_p2=s;u=this._;l=true;a:while(l===true){l=false;d=true;g:while(d===true){d=false;w=this._;e=true;b:while(e===true){e=false;if(!f(this,b.g_v,97,252)){break b}g=true;f:while(g===true){g=false;x=this._;i=true;c:while(i===true){i=false;if(!h(this,b.g_v,97,252)){break c}d:while(true){c=true;e:while(c===true){c=false;if(!f(this,b.g_v,97,252)){break e}break d}if(this._>=this.A){break c}this._++}break f}this._=x;if(!f(this,b.g_v,97,252)){break b}c:while(true){j=true;d:while(j===true){j=false;if(!h(this,b.g_v,97,252)){break d}break c}if(this._>=this.A){break b}this._++}}break g}this._=w;if(!h(this,b.g_v,97,252)){break a}k=true;c:while(k===true){k=false;y=this._;a=true;b:while(a===true){a=false;if(!h(this,b.g_v,97,252)){break b}e:while(true){m=true;d:while(m===true){m=false;if(!f(this,b.g_v,97,252)){break d}break e}if(this._>=this.A){break b}this._++}break c}this._=y;if(!f(this,b.g_v,97,252)){break a}if(this._>=this.A){break a}this._++}}this.I_pV=this._}v=this._=u;t=v;n=true;a:while(n===true){n=false;b:while(true){o=true;c:while(o===true){o=false;if(!f(this,b.g_v,97,252)){break c}break b}if(this._>=this.A){break a}this._++}b:while(true){p=true;c:while(p===true){p=false;if(!h(this,b.g_v,97,252)){break c}break b}if(this._>=this.A){break a}this._++}this.I_p1=this._;b:while(true){q=true;c:while(q===true){q=false;if(!f(this,b.g_v,97,252)){break c}break b}if(this._>=this.A){break a}this._++}c:while(true){r=true;b:while(r===true){r=false;if(!h(this,b.g_v,97,252)){break b}break c}if(this._>=this.A){break a}this._++}this.I_p2=this._}this._=t;return true};b.prototype.r_mark_regions=b.prototype.U;function E(a){var x;var y;var z;var u;var v;var l;var d;var e;var g;var i;var j;var k;var c;var m;var n;var o;var p;var q;var r;var s;var t;var w;a.I_pV=t=a.A;a.I_p1=t;a.I_p2=t;x=a._;l=true;a:while(l===true){l=false;d=true;g:while(d===true){d=false;y=a._;e=true;b:while(e===true){e=false;if(!f(a,b.g_v,97,252)){break b}g=true;f:while(g===true){g=false;z=a._;i=true;c:while(i===true){i=false;if(!h(a,b.g_v,97,252)){break c}d:while(true){j=true;e:while(j===true){j=false;if(!f(a,b.g_v,97,252)){break e}break d}if(a._>=a.A){break c}a._++}break f}a._=z;if(!f(a,b.g_v,97,252)){break b}c:while(true){k=true;d:while(k===true){k=false;if(!h(a,b.g_v,97,252)){break d}break c}if(a._>=a.A){break b}a._++}}break g}a._=y;if(!h(a,b.g_v,97,252)){break a}c=true;c:while(c===true){c=false;u=a._;m=true;b:while(m===true){m=false;if(!h(a,b.g_v,97,252)){break b}e:while(true){n=true;d:while(n===true){n=false;if(!f(a,b.g_v,97,252)){break d}break e}if(a._>=a.A){break b}a._++}break c}a._=u;if(!f(a,b.g_v,97,252)){break a}if(a._>=a.A){break a}a._++}}a.I_pV=a._}w=a._=x;v=w;o=true;a:while(o===true){o=false;b:while(true){p=true;c:while(p===true){p=false;if(!f(a,b.g_v,97,252)){break c}break b}if(a._>=a.A){break a}a._++}b:while(true){q=true;c:while(q===true){q=false;if(!h(a,b.g_v,97,252)){break c}break b}if(a._>=a.A){break a}a._++}a.I_p1=a._;b:while(true){r=true;c:while(r===true){r=false;if(!f(a,b.g_v,97,252)){break c}break b}if(a._>=a.A){break a}a._++}c:while(true){s=true;b:while(s===true){s=false;if(!h(a,b.g_v,97,252)){break b}break c}if(a._>=a.A){break a}a._++}a.I_p2=a._}a._=v;return true};b.prototype.V=function(){var a;var e;var d;b:while(true){e=this._;d=true;a:while(d===true){d=false;this.B=this._;a=n(this,b.a_0,6);if(a===0){break a}this.C=this._;switch(a){case 0:break a;case 1:if(!c(this,'a')){return false}break;case 2:if(!c(this,'e')){return false}break;case 3:if(!c(this,'i')){return false}break;case 4:if(!c(this,'o')){return false}break;case 5:if(!c(this,'u')){return false}break;case 6:if(this._>=this.A){break a}this._++;break}continue b}this._=e;break b}return true};b.prototype.r_postlude=b.prototype.V;function F(a){var d;var f;var e;b:while(true){f=a._;e=true;a:while(e===true){e=false;a.B=a._;d=n(a,b.a_0,6);if(d===0){break a}a.C=a._;switch(d){case 0:break a;case 1:if(!c(a,'a')){return false}break;case 2:if(!c(a,'e')){return false}break;case 3:if(!c(a,'i')){return false}break;case 4:if(!c(a,'o')){return false}break;case 5:if(!c(a,'u')){return false}break;case 6:if(a._>=a.A){break a}a._++;break}continue b}a._=f;break b}return true};b.prototype.S=function(){return!(this.I_pV<=this._)?false:true};b.prototype.r_RV=b.prototype.S;b.prototype.Q=function(){return!(this.I_p1<=this._)?false:true};b.prototype.r_R1=b.prototype.Q;b.prototype.R=function(){return!(this.I_p2<=this._)?false:true};b.prototype.r_R2=b.prototype.R;b.prototype.T=function(){var a;this.C=this._;if(e(this,b.a_1,13)===0){return false}this.B=this._;a=e(this,b.a_2,11);if(a===0){return false}if(!(!(this.I_pV<=this._)?false:true)){return false}switch(a){case 0:return false;case 1:this.B=this._;if(!c(this,'iendo')){return false}break;case 2:this.B=this._;if(!c(this,'ando')){return false}break;case 3:this.B=this._;if(!c(this,'ar')){return false}break;case 4:this.B=this._;if(!c(this,'er')){return false}break;case 5:this.B=this._;if(!c(this,'ir')){return false}break;case 6:if(!c(this,'')){return false}break;case 7:if(!d(this,1,'u')){return false}if(!c(this,'')){return false}break}return true};b.prototype.r_attached_pronoun=b.prototype.T;function G(a){var f;a.C=a._;if(e(a,b.a_1,13)===0){return false}a.B=a._;f=e(a,b.a_2,11);if(f===0){return false}if(!(!(a.I_pV<=a._)?false:true)){return false}switch(f){case 0:return false;case 1:a.B=a._;if(!c(a,'iendo')){return false}break;case 2:a.B=a._;if(!c(a,'ando')){return false}break;case 3:a.B=a._;if(!c(a,'ar')){return false}break;case 4:a.B=a._;if(!c(a,'er')){return false}break;case 5:a.B=a._;if(!c(a,'ir')){return false}break;case 6:if(!c(a,'')){return false}break;case 7:if(!d(a,1,'u')){return false}if(!c(a,'')){return false}break}return true};b.prototype.X=function(){var a;var j;var f;var g;var h;var i;var k;var l;var m;var n;var o;var q;var r;var s;var p;this.C=this._;a=e(this,b.a_6,46);if(a===0){return false}this.B=this._;switch(a){case 0:return false;case 1:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}break;case 2:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}j=this.A-this._;k=true;a:while(k===true){k=false;this.C=this._;if(!d(this,2,'ic')){this._=this.A-j;break a}this.B=q=this._;if(!(!(this.I_p2<=q)?false:true)){this._=this.A-j;break a}if(!c(this,'')){return false}}break;case 3:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'log')){return false}break;case 4:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'u')){return false}break;case 5:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'ente')){return false}break;case 6:if(!(!(this.I_p1<=this._)?false:true)){return false}if(!c(this,'')){return false}f=this.A-this._;l=true;a:while(l===true){l=false;this.C=this._;a=e(this,b.a_3,4);if(a===0){this._=this.A-f;break a}this.B=r=this._;if(!(!(this.I_p2<=r)?false:true)){this._=this.A-f;break a}if(!c(this,'')){return false}switch(a){case 0:this._=this.A-f;break a;case 1:this.C=this._;if(!d(this,2,'at')){this._=this.A-f;break a}this.B=s=this._;if(!(!(this.I_p2<=s)?false:true)){this._=this.A-f;break a}if(!c(this,'')){return false}break}}break;case 7:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}g=this.A-this._;m=true;a:while(m===true){m=false;this.C=this._;a=e(this,b.a_4,3);if(a===0){this._=this.A-g;break a}this.B=this._;switch(a){case 0:this._=this.A-g;break a;case 1:if(!(!(this.I_p2<=this._)?false:true)){this._=this.A-g;break a}if(!c(this,'')){return false}break}}break;case 8:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}h=this.A-this._;n=true;a:while(n===true){n=false;this.C=this._;a=e(this,b.a_5,3);if(a===0){this._=this.A-h;break a}this.B=this._;switch(a){case 0:this._=this.A-h;break a;case 1:if(!(!(this.I_p2<=this._)?false:true)){this._=this.A-h;break a}if(!c(this,'')){return false}break}}break;case 9:if(!(!(this.I_p2<=this._)?false:true)){return false}if(!c(this,'')){return false}i=this.A-this._;o=true;a:while(o===true){o=false;this.C=this._;if(!d(this,2,'at')){this._=this.A-i;break a}this.B=p=this._;if(!(!(this.I_p2<=p)?false:true)){this._=this.A-i;break a}if(!c(this,'')){return false}}break}return true};b.prototype.r_standard_suffix=b.prototype.X;function H(a){var f;var k;var g;var h;var i;var j;var l;var m;var n;var o;var p;var r;var s;var t;var q;a.C=a._;f=e(a,b.a_6,46);if(f===0){return false}a.B=a._;switch(f){case 0:return false;case 1:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}break;case 2:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}k=a.A-a._;l=true;a:while(l===true){l=false;a.C=a._;if(!d(a,2,'ic')){a._=a.A-k;break a}a.B=r=a._;if(!(!(a.I_p2<=r)?false:true)){a._=a.A-k;break a}if(!c(a,'')){return false}}break;case 3:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'log')){return false}break;case 4:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'u')){return false}break;case 5:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'ente')){return false}break;case 6:if(!(!(a.I_p1<=a._)?false:true)){return false}if(!c(a,'')){return false}g=a.A-a._;m=true;a:while(m===true){m=false;a.C=a._;f=e(a,b.a_3,4);if(f===0){a._=a.A-g;break a}a.B=s=a._;if(!(!(a.I_p2<=s)?false:true)){a._=a.A-g;break a}if(!c(a,'')){return false}switch(f){case 0:a._=a.A-g;break a;case 1:a.C=a._;if(!d(a,2,'at')){a._=a.A-g;break a}a.B=t=a._;if(!(!(a.I_p2<=t)?false:true)){a._=a.A-g;break a}if(!c(a,'')){return false}break}}break;case 7:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}h=a.A-a._;n=true;a:while(n===true){n=false;a.C=a._;f=e(a,b.a_4,3);if(f===0){a._=a.A-h;break a}a.B=a._;switch(f){case 0:a._=a.A-h;break a;case 1:if(!(!(a.I_p2<=a._)?false:true)){a._=a.A-h;break a}if(!c(a,'')){return false}break}}break;case 8:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}i=a.A-a._;o=true;a:while(o===true){o=false;a.C=a._;f=e(a,b.a_5,3);if(f===0){a._=a.A-i;break a}a.B=a._;switch(f){case 0:a._=a.A-i;break a;case 1:if(!(!(a.I_p2<=a._)?false:true)){a._=a.A-i;break a}if(!c(a,'')){return false}break}}break;case 9:if(!(!(a.I_p2<=a._)?false:true)){return false}if(!c(a,'')){return false}j=a.A-a._;p=true;a:while(p===true){p=false;a.C=a._;if(!d(a,2,'at')){a._=a.A-j;break a}a.B=q=a._;if(!(!(a.I_p2<=q)?false:true)){a._=a.A-j;break a}if(!c(a,'')){return false}}break}return true};b.prototype.Z=function(){var a;var g;var f;var h;var i;var j;g=this.A-(h=this._);if(h<this.I_pV){return false}i=this._=this.I_pV;f=this.D;this.D=i;j=this._=this.A-g;this.C=j;a=e(this,b.a_7,12);if(a===0){this.D=f;return false}this.B=this._;this.D=f;switch(a){case 0:return false;case 1:if(!d(this,1,'u')){return false}if(!c(this,'')){return false}break}return true};b.prototype.r_y_verb_suffix=b.prototype.Z;function D(a){var f;var h;var g;var i;var j;var k;h=a.A-(i=a._);if(i<a.I_pV){return false}j=a._=a.I_pV;g=a.D;a.D=j;k=a._=a.A-h;a.C=k;f=e(a,b.a_7,12);if(f===0){a.D=g;return false}a.B=a._;a.D=g;switch(f){case 0:return false;case 1:if(!d(a,1,'u')){return false}if(!c(a,'')){return false}break}return true};b.prototype.Y=function(){var a;var i;var f;var g;var j;var h;var k;var l;var m;i=this.A-(k=this._);if(k<this.I_pV){return false}l=this._=this.I_pV;f=this.D;this.D=l;m=this._=this.A-i;this.C=m;a=e(this,b.a_8,96);if(a===0){this.D=f;return false}this.B=this._;this.D=f;switch(a){case 0:return false;case 1:g=this.A-this._;h=true;a:while(h===true){h=false;if(!d(this,1,'u')){this._=this.A-g;break a}j=this.A-this._;if(!d(this,1,'g')){this._=this.A-g;break a}this._=this.A-j}this.B=this._;if(!c(this,'')){return false}break;case 2:if(!c(this,'')){return false}break}return true};b.prototype.r_verb_suffix=b.prototype.Y;function C(a){var g;var j;var h;var f;var k;var i;var m;var n;var l;j=a.A-(m=a._);if(m<a.I_pV){return false}n=a._=a.I_pV;h=a.D;a.D=n;l=a._=a.A-j;a.C=l;g=e(a,b.a_8,96);if(g===0){a.D=h;return false}a.B=a._;a.D=h;switch(g){case 0:return false;case 1:f=a.A-a._;i=true;a:while(i===true){i=false;if(!d(a,1,'u')){a._=a.A-f;break a}k=a.A-a._;if(!d(a,1,'g')){a._=a.A-f;break a}a._=a.A-k}a.B=a._;if(!c(a,'')){return false}break;case 2:if(!c(a,'')){return false}break}return true};b.prototype.W=function(){var f;var a;var h;var g;var i;var j;this.C=this._;f=e(this,b.a_9,8);if(f===0){return false}this.B=this._;switch(f){case 0:return false;case 1:if(!(!(this.I_pV<=this._)?false:true)){return false}if(!c(this,'')){return false}break;case 2:if(!(!(this.I_pV<=this._)?false:true)){return false}if(!c(this,'')){return false}a=this.A-this._;g=true;a:while(g===true){g=false;this.C=this._;if(!d(this,1,'u')){this._=this.A-a;break a}this.B=i=this._;h=this.A-i;if(!d(this,1,'g')){this._=this.A-a;break a}j=this._=this.A-h;if(!(!(this.I_pV<=j)?false:true)){this._=this.A-a;break a}if(!c(this,'')){return false}}break}return true};b.prototype.r_residual_suffix=b.prototype.W;function y(a){var g;var f;var i;var h;var j;var k;a.C=a._;g=e(a,b.a_9,8);if(g===0){return false}a.B=a._;switch(g){case 0:return false;case 1:if(!(!(a.I_pV<=a._)?false:true)){return false}if(!c(a,'')){return false}break;case 2:if(!(!(a.I_pV<=a._)?false:true)){return false}if(!c(a,'')){return false}f=a.A-a._;h=true;a:while(h===true){h=false;a.C=a._;if(!d(a,1,'u')){a._=a.A-f;break a}a.B=j=a._;i=a.A-j;if(!d(a,1,'g')){a._=a.A-f;break a}k=a._=a.A-i;if(!(!(a.I_pV<=k)?false:true)){a._=a.A-f;break a}if(!c(a,'')){return false}}break}return true};b.prototype.J=function(){var k;var l;var m;var b;var j;var c;var d;var e;var f;var a;var g;var h;var i;var o;var p;var q;var r;var s;var n;k=this._;c=true;a:while(c===true){c=false;if(!E(this)){break a}}o=this._=k;this.D=o;q=this._=p=this.A;l=p-q;d=true;a:while(d===true){d=false;if(!G(this)){break a}}s=this._=(r=this.A)-l;m=r-s;e=true;b:while(e===true){e=false;f=true;a:while(f===true){f=false;b=this.A-this._;a=true;c:while(a===true){a=false;if(!H(this)){break c}break a}this._=this.A-b;g=true;c:while(g===true){g=false;if(!D(this)){break c}break a}this._=this.A-b;if(!C(this)){break b}}}this._=this.A-m;h=true;a:while(h===true){h=false;if(!y(this)){break a}}n=this._=this.D;j=n;i=true;a:while(i===true){i=false;if(!F(this)){break a}}this._=j;return true};b.prototype.stem=b.prototype.J;b.prototype.N=function(a){return a instanceof b};b.prototype.equals=b.prototype.N;b.prototype.O=function(){var c;var a;var b;var d;c='SpanishStemmer';a=0;for(b=0;b<c.length;b++){d=c.charCodeAt(b);a=(a<<5)-a+d;a=a&a}return a|0};b.prototype.hashCode=b.prototype.O;b.serialVersionUID=1;g(b,'methodObject',function(){return new b});g(b,'a_0',function(){return[new a('',-1,6),new a('á',0,1),new a('é',0,2),new a('í',0,3),new a('ó',0,4),new a('ú',0,5)]});g(b,'a_1',function(){return[new a('la',-1,-1),new a('sela',0,-1),new a('le',-1,-1),new a('me',-1,-1),new a('se',-1,-1),new a('lo',-1,-1),new a('selo',5,-1),new a('las',-1,-1),new a('selas',7,-1),new a('les',-1,-1),new a('los',-1,-1),new a('selos',10,-1),new a('nos',-1,-1)]});g(b,'a_2',function(){return[new a('ando',-1,6),new a('iendo',-1,6),new a('yendo',-1,7),new a('ándo',-1,2),new a('iéndo',-1,1),new a('ar',-1,6),new a('er',-1,6),new a('ir',-1,6),new a('ár',-1,3),new a('ér',-1,4),new a('ír',-1,5)]});g(b,'a_3',function(){return[new a('ic',-1,-1),new a('ad',-1,-1),new a('os',-1,-1),new a('iv',-1,1)]});g(b,'a_4',function(){return[new a('able',-1,1),new a('ible',-1,1),new a('ante',-1,1)]});g(b,'a_5',function(){return[new a('ic',-1,1),new a('abil',-1,1),new a('iv',-1,1)]});g(b,'a_6',function(){return[new a('ica',-1,1),new a('ancia',-1,2),new a('encia',-1,5),new a('adora',-1,2),new a('osa',-1,1),new a('ista',-1,1),new a('iva',-1,9),new a('anza',-1,1),new a('logía',-1,3),new a('idad',-1,8),new a('able',-1,1),new a('ible',-1,1),new a('ante',-1,2),new a('mente',-1,7),new a('amente',13,6),new a('ación',-1,2),new a('ución',-1,4),new a('ico',-1,1),new a('ismo',-1,1),new a('oso',-1,1),new a('amiento',-1,1),new a('imiento',-1,1),new a('ivo',-1,9),new a('ador',-1,2),new a('icas',-1,1),new a('ancias',-1,2),new a('encias',-1,5),new a('adoras',-1,2),new a('osas',-1,1),new a('istas',-1,1),new a('ivas',-1,9),new a('anzas',-1,1),new a('logías',-1,3),new a('idades',-1,8),new a('ables',-1,1),new a('ibles',-1,1),new a('aciones',-1,2),new a('uciones',-1,4),new a('adores',-1,2),new a('antes',-1,2),new a('icos',-1,1),new a('ismos',-1,1),new a('osos',-1,1),new a('amientos',-1,1),new a('imientos',-1,1),new a('ivos',-1,9)]});g(b,'a_7',function(){return[new a('ya',-1,1),new a('ye',-1,1),new a('yan',-1,1),new a('yen',-1,1),new a('yeron',-1,1),new a('yendo',-1,1),new a('yo',-1,1),new a('yas',-1,1),new a('yes',-1,1),new a('yais',-1,1),new a('yamos',-1,1),new a('yó',-1,1)]});g(b,'a_8',function(){return[new a('aba',-1,2),new a('ada',-1,2),new a('ida',-1,2),new a('ara',-1,2),new a('iera',-1,2),new a('ía',-1,2),new a('aría',5,2),new a('ería',5,2),new a('iría',5,2),new a('ad',-1,2),new a('ed',-1,2),new a('id',-1,2),new a('ase',-1,2),new a('iese',-1,2),new a('aste',-1,2),new a('iste',-1,2),new a('an',-1,2),new a('aban',16,2),new a('aran',16,2),new a('ieran',16,2),new a('ían',16,2),new a('arían',20,2),new a('erían',20,2),new a('irían',20,2),new a('en',-1,1),new a('asen',24,2),new a('iesen',24,2),new a('aron',-1,2),new a('ieron',-1,2),new a('arán',-1,2),new a('erán',-1,2),new a('irán',-1,2),new a('ado',-1,2),new a('ido',-1,2),new a('ando',-1,2),new a('iendo',-1,2),new a('ar',-1,2),new a('er',-1,2),new a('ir',-1,2),new a('as',-1,2),new a('abas',39,2),new a('adas',39,2),new a('idas',39,2),new a('aras',39,2),new a('ieras',39,2),new a('ías',39,2),new a('arías',45,2),new a('erías',45,2),new a('irías',45,2),new a('es',-1,1),new a('ases',49,2),new a('ieses',49,2),new a('abais',-1,2),new a('arais',-1,2),new a('ierais',-1,2),new a('íais',-1,2),new a('aríais',55,2),new a('eríais',55,2),new a('iríais',55,2),new a('aseis',-1,2),new a('ieseis',-1,2),new a('asteis',-1,2),new a('isteis',-1,2),new a('áis',-1,2),new a('éis',-1,1),new a('aréis',64,2),new a('eréis',64,2),new a('iréis',64,2),new a('ados',-1,2),new a('idos',-1,2),new a('amos',-1,2),new a('ábamos',70,2),new a('áramos',70,2),new a('iéramos',70,2),new a('íamos',70,2),new a('aríamos',74,2),new a('eríamos',74,2),new a('iríamos',74,2),new a('emos',-1,1),new a('aremos',78,2),new a('eremos',78,2),new a('iremos',78,2),new a('ásemos',78,2),new a('iésemos',78,2),new a('imos',-1,2),new a('arás',-1,2),new a('erás',-1,2),new a('irás',-1,2),new a('ís',-1,2),new a('ará',-1,2),new a('erá',-1,2),new a('irá',-1,2),new a('aré',-1,2),new a('eré',-1,2),new a('iré',-1,2),new a('ió',-1,2)]});g(b,'a_9',function(){return[new a('a',-1,1),new a('e',-1,2),new a('o',-1,1),new a('os',-1,1),new a('á',-1,1),new a('é',-1,2),new a('í',-1,1),new a('ó',-1,1)]});g(b,'g_v',function(){return[17,65,16,0,0,0,0,0,0,0,0,0,0,0,0,0,1,17,4,10]});var o={'src/stemmer.jsx':{Stemmer:m},'src/spanish-stemmer.jsx':{SpanishStemmer:b}}}(JSX))
var Stemmer = JSX.require("src/spanish-stemmer.jsx").SpanishStemmer;
"""


class SearchSpanish(SearchLanguage):
    lang = 'es'
    language_name = 'Spanish'
    js_stemmer_rawcode = 'spanish-stemmer.js'
    js_stemmer_code = js_stemmer
    stopwords = spanish_stopwords

    def init(self, options):
        # type: (Any) -> None
        self.stemmer = snowballstemmer.stemmer('spanish')

    def stem(self, word):
        # type: (unicode) -> unicode
        return self.stemmer.stemWord(word.lower())
