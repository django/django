# -*- coding: utf-8 -*-
"""
    sphinx.search.ru
    ~~~~~~~~~~~~~~~~

    Russian search language: includes the JS Russian stemmer.

    :copyright: Copyright 2007-2013 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from sphinx.search import SearchLanguage, parse_stop_word

import snowballstemmer

if False:
    # For type annotation
    from typing import Any  # NOQA


russian_stopwords = parse_stop_word(u'''
| source: http://snowball.tartarus.org/algorithms/russian/stop.txt
и              | and
в              | in/into
во             | alternative form
не             | not
что            | what/that
он             | he
на             | on/onto
я              | i
с              | from
со             | alternative form
как            | how
а              | milder form of `no' (but)
то             | conjunction and form of `that'
все            | all
она            | she
так            | so, thus
его            | him
но             | but
да             | yes/and
ты             | thou
к              | towards, by
у              | around, chez
же             | intensifier particle
вы             | you
за             | beyond, behind
бы             | conditional/subj. particle
по             | up to, along
только         | only
ее             | her
мне            | to me
было           | it was
вот            | here is/are, particle
от             | away from
меня           | me
еще            | still, yet, more
нет            | no, there isnt/arent
о              | about
из             | out of
ему            | to him
теперь         | now
когда          | when
даже           | even
ну             | so, well
вдруг          | suddenly
ли             | interrogative particle
если           | if
уже            | already, but homonym of `narrower'
или            | or
ни             | neither
быть           | to be
был            | he was
него           | prepositional form of его
до             | up to
вас            | you accusative
нибудь         | indef. suffix preceded by hyphen
опять          | again
уж             | already, but homonym of `adder'
вам            | to you
сказал         | he said
ведь           | particle `after all'
там            | there
потом          | then
себя           | oneself
ничего         | nothing
ей             | to her
может          | usually with `быть' as `maybe'
они            | they
тут            | here
где            | where
есть           | there is/are
надо           | got to, must
ней            | prepositional form of  ей
для            | for
мы             | we
тебя           | thee
их             | them, their
чем            | than
была           | she was
сам            | self
чтоб           | in order to
без            | without
будто          | as if
человек        | man, person, one
чего           | genitive form of `what'
раз            | once
тоже           | also
себе           | to oneself
под            | beneath
жизнь          | life
будет          | will be
ж              | short form of intensifer particle `же'
тогда          | then
кто            | who
этот           | this
говорил        | was saying
того           | genitive form of `that'
потому         | for that reason
этого          | genitive form of `this'
какой          | which
совсем         | altogether
ним            | prepositional form of `его', `они'
здесь          | here
этом           | prepositional form of `этот'
один           | one
почти          | almost
мой            | my
тем            | instrumental/dative plural of `тот', `то'
чтобы          | full form of `in order that'
нее            | her (acc.)
кажется        | it seems
сейчас         | now
были           | they were
куда           | where to
зачем          | why
сказать        | to say
всех           | all (acc., gen. preposn. plural)
никогда        | never
сегодня        | today
можно          | possible, one can
при            | by
наконец        | finally
два            | two
об             | alternative form of `о', about
другой         | another
хоть           | even
после          | after
над            | above
больше         | more
тот            | that one (masc.)
через          | across, in
эти            | these
нас            | us
про            | about
всего          | in all, only, of all
них            | prepositional form of `они' (they)
какая          | which, feminine
много          | lots
разве          | interrogative particle
сказала        | she said
три            | three
эту            | this, acc. fem. sing.
моя            | my, feminine
впрочем        | moreover, besides
хорошо         | good
свою           | ones own, acc. fem. sing.
этой           | oblique form of `эта', fem. `this'
перед          | in front of
иногда         | sometimes
лучше          | better
чуть           | a little
том            | preposn. form of `that one'
нельзя         | one must not
такой          | such a one
им             | to them
более          | more
всегда         | always
конечно        | of course
всю            | acc. fem. sing of `all'
между          | between


  | b: some paradigms
  |
  | personal pronouns
  |
  | я  меня  мне  мной  [мною]
  | ты  тебя  тебе  тобой  [тобою]
  | он  его  ему  им  [него, нему, ним]
  | она  ее  эи  ею  [нее, нэи, нею]
  | оно  его  ему  им  [него, нему, ним]
  |
  | мы  нас  нам  нами
  | вы  вас  вам  вами
  | они  их  им  ими  [них, ним, ними]
  |
  |   себя  себе  собой   [собою]
  |
  | demonstrative pronouns: этот (this), тот (that)
  |
  | этот  эта  это  эти
  | этого  эты  это  эти
  | этого  этой  этого  этих
  | этому  этой  этому  этим
  | этим  этой  этим  [этою]  этими
  | этом  этой  этом  этих
  |
  | тот  та  то  те
  | того  ту  то  те
  | того  той  того  тех
  | тому  той  тому  тем
  | тем  той  тем  [тою]  теми
  | том  той  том  тех
  |
  | determinative pronouns
  |
  | (a) весь (all)
  |
  | весь  вся  все  все
  | всего  всю  все  все
  | всего  всей  всего  всех
  | всему  всей  всему  всем
  | всем  всей  всем  [всею]  всеми
  | всем  всей  всем  всех
  |
  | (b) сам (himself etc)
  |
  | сам  сама  само  сами
  | самого саму  само  самих
  | самого самой самого  самих
  | самому самой самому  самим
  | самим  самой  самим  [самою]  самими
  | самом самой самом  самих
  |
  | stems of verbs `to be', `to have', `to do' and modal
  |
  | быть  бы  буд  быв  есть  суть
  | име
  | дел
  | мог   мож  мочь
  | уме
  | хоч  хот
  | долж
  | можн
  | нужн
  | нельзя
''')

js_stemmer = u"""
var JSX={};(function(h){function j(b,e){var a=function(){};a.prototype=e.prototype;var c=new a;for(var d in b){b[d].prototype=c}}function J(c,b){for(var a in b.prototype)if(b.prototype.hasOwnProperty(a))c.prototype[a]=b.prototype[a]}function f(a,b,d){function c(a,b,c){delete a[b];a[b]=c;return c}Object.defineProperty(a,b,{get:function(){return c(a,b,d())},set:function(d){c(a,b,d)},enumerable:true,configurable:true})}function K(a,b,c){return a[b]=a[b]/c|0}var p=parseInt;var z=parseFloat;function L(a){return a!==a}var x=isFinite;var w=encodeURIComponent;var u=decodeURIComponent;var t=encodeURI;var s=decodeURI;var B=Object.prototype.toString;var q=Object.prototype.hasOwnProperty;function i(){}h.require=function(b){var a=o[b];return a!==undefined?a:null};h.profilerIsRunning=function(){return i.getResults!=null};h.getProfileResults=function(){return(i.getResults||function(){return{}})()};h.postProfileResults=function(a,b){if(i.postResults==null)throw new Error('profiler has not been turned on');return i.postResults(a,b)};h.resetProfileResults=function(){if(i.resetResults==null)throw new Error('profiler has not been turned on');return i.resetResults()};h.DEBUG=false;function r(){};j([r],Error);function a(a,b,c){this.G=a.length;this.X=a;this.a=b;this.J=c;this.I=null;this.b=null};j([a],Object);function m(){};j([m],Object);function g(){var a;var b;var c;this.F={};a=this.D='';b=this._=0;c=this.A=a.length;this.E=0;this.B=b;this.C=c};j([g],m);function v(a,b){a.D=b.D;a._=b._;a.A=b.A;a.E=b.E;a.B=b.B;a.C=b.C};function k(b,d,c,e){var a;if(b._>=b.A){return false}a=b.D.charCodeAt(b._);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._++;return true};function l(a,d,c,e){var b;if(a._>=a.A){return false}b=a.D.charCodeAt(a._);if(b>e||b<c){a._++;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._++;return true}return false};function d(a,b,d){var c;if(a._-a.E<b){return false}if(a.D.slice((c=a._)-b,c)!==d){return false}a._-=b;return true};function e(d,m,p){var b;var g;var e;var n;var f;var k;var l;var i;var h;var c;var a;var j;var o;b=0;g=p;e=d._;n=d.E;f=0;k=0;l=false;while(true){i=b+(g-b>>1);h=0;c=f<k?f:k;a=m[i];for(j=a.G-1-c;j>=0;j--){if(e-c===n){h=-1;break}h=d.D.charCodeAt(e-1-c)-a.X.charCodeAt(j);if(h!==0){break}c++}if(h<0){g=i;k=c}else{b=i;f=c}if(g-b<=1){if(b>0){break}if(g===b){break}if(l){break}l=true}}while(true){a=m[b];if(f>=a.G){d._=e-a.G|0;if(a.I==null){return a.J}o=a.I(d);d._=e-a.G|0;if(o){return a.J}}b=a.a;if(b<0){return 0}}return-1};function A(a,b,d,e){var c;c=e.length-(d-b);a.D=a.D.slice(0,b)+e+a.D.slice(d);a.A+=c|0;if(a._>=d){a._+=c|0}else if(a._>b){a._=b}return c|0};function c(a,f){var b;var c;var d;var e;b=false;if((c=a.B)<0||c>(d=a.C)||d>(e=a.A)||e>a.D.length?false:true){A(a,a.B,a.C,f);b=true}return b};g.prototype.H=function(){return false};g.prototype.Y=function(b){var a;var c;var d;var e;a=this.F['.'+b];if(a==null){c=this.D=b;d=this._=0;e=this.A=c.length;this.E=0;this.B=d;this.C=e;this.H();a=this.D;this.F['.'+b]=a}return a};g.prototype.stemWord=g.prototype.Y;g.prototype.Z=function(e){var d;var b;var c;var a;var f;var g;var h;d=[];for(b=0;b<e.length;b++){c=e[b];a=this.F['.'+c];if(a==null){f=this.D=c;g=this._=0;h=this.A=f.length;this.E=0;this.B=g;this.C=h;this.H();a=this.D;this.F['.'+c]=a}d.push(a)}return d};g.prototype.stemWords=g.prototype.Z;function b(){g.call(this);this.I_p2=0;this.I_pV=0};j([b],g);b.prototype.K=function(a){this.I_p2=a.I_p2;this.I_pV=a.I_pV;v(this,a)};b.prototype.copy_from=b.prototype.K;b.prototype.R=function(){var g;var a;var c;var d;var e;var f;var h;this.I_pV=h=this.A;this.I_p2=h;g=this._;a=true;a:while(a===true){a=false;b:while(true){c=true;c:while(c===true){c=false;if(!k(this,b.g_v,1072,1103)){break c}break b}if(this._>=this.A){break a}this._++}this.I_pV=this._;b:while(true){d=true;c:while(d===true){d=false;if(!l(this,b.g_v,1072,1103)){break c}break b}if(this._>=this.A){break a}this._++}b:while(true){e=true;c:while(e===true){e=false;if(!k(this,b.g_v,1072,1103)){break c}break b}if(this._>=this.A){break a}this._++}b:while(true){f=true;c:while(f===true){f=false;if(!l(this,b.g_v,1072,1103)){break c}break b}if(this._>=this.A){break a}this._++}this.I_p2=this._}this._=g;return true};b.prototype.r_mark_regions=b.prototype.R;function D(a){var h;var c;var d;var e;var f;var g;var i;a.I_pV=i=a.A;a.I_p2=i;h=a._;c=true;a:while(c===true){c=false;b:while(true){d=true;c:while(d===true){d=false;if(!k(a,b.g_v,1072,1103)){break c}break b}if(a._>=a.A){break a}a._++}a.I_pV=a._;b:while(true){e=true;c:while(e===true){e=false;if(!l(a,b.g_v,1072,1103)){break c}break b}if(a._>=a.A){break a}a._++}b:while(true){f=true;c:while(f===true){f=false;if(!k(a,b.g_v,1072,1103)){break c}break b}if(a._>=a.A){break a}a._++}b:while(true){g=true;c:while(g===true){g=false;if(!l(a,b.g_v,1072,1103)){break c}break b}if(a._>=a.A){break a}a._++}a.I_p2=a._}a._=h;return true};b.prototype.N=function(){return!(this.I_p2<=this._)?false:true};b.prototype.r_R2=b.prototype.N;b.prototype.T=function(){var a;var h;var f;var g;this.C=this._;a=e(this,b.a_0,9);if(a===0){return false}this.B=this._;switch(a){case 0:return false;case 1:f=true;a:while(f===true){f=false;h=this.A-this._;g=true;b:while(g===true){g=false;if(!d(this,1,'а')){break b}break a}this._=this.A-h;if(!d(this,1,'я')){return false}}if(!c(this,'')){return false}break;case 2:if(!c(this,'')){return false}break}return true};b.prototype.r_perfective_gerund=b.prototype.T;function E(a){var f;var i;var g;var h;a.C=a._;f=e(a,b.a_0,9);if(f===0){return false}a.B=a._;switch(f){case 0:return false;case 1:g=true;a:while(g===true){g=false;i=a.A-a._;h=true;b:while(h===true){h=false;if(!d(a,1,'а')){break b}break a}a._=a.A-i;if(!d(a,1,'я')){return false}}if(!c(a,'')){return false}break;case 2:if(!c(a,'')){return false}break}return true};b.prototype.P=function(){var a;this.C=this._;a=e(this,b.a_1,26);if(a===0){return false}this.B=this._;switch(a){case 0:return false;case 1:if(!c(this,'')){return false}break}return true};b.prototype.r_adjective=b.prototype.P;function n(a){var d;a.C=a._;d=e(a,b.a_1,26);if(d===0){return false}a.B=a._;switch(d){case 0:return false;case 1:if(!c(a,'')){return false}break}return true};b.prototype.O=function(){var f;var a;var j;var g;var h;var i;if(!n(this)){return false}a=this.A-this._;g=true;a:while(g===true){g=false;this.C=this._;f=e(this,b.a_2,8);if(f===0){this._=this.A-a;break a}this.B=this._;switch(f){case 0:this._=this.A-a;break a;case 1:h=true;b:while(h===true){h=false;j=this.A-this._;i=true;c:while(i===true){i=false;if(!d(this,1,'а')){break c}break b}this._=this.A-j;if(!d(this,1,'я')){this._=this.A-a;break a}}if(!c(this,'')){return false}break;case 2:if(!c(this,'')){return false}break}}return true};b.prototype.r_adjectival=b.prototype.O;function G(a){var g;var f;var k;var h;var i;var j;if(!n(a)){return false}f=a.A-a._;h=true;a:while(h===true){h=false;a.C=a._;g=e(a,b.a_2,8);if(g===0){a._=a.A-f;break a}a.B=a._;switch(g){case 0:a._=a.A-f;break a;case 1:i=true;b:while(i===true){i=false;k=a.A-a._;j=true;c:while(j===true){j=false;if(!d(a,1,'а')){break c}break b}a._=a.A-k;if(!d(a,1,'я')){a._=a.A-f;break a}}if(!c(a,'')){return false}break;case 2:if(!c(a,'')){return false}break}}return true};b.prototype.U=function(){var a;this.C=this._;a=e(this,b.a_3,2);if(a===0){return false}this.B=this._;switch(a){case 0:return false;case 1:if(!c(this,'')){return false}break}return true};b.prototype.r_reflexive=b.prototype.U;function H(a){var d;a.C=a._;d=e(a,b.a_3,2);if(d===0){return false}a.B=a._;switch(d){case 0:return false;case 1:if(!c(a,'')){return false}break}return true};b.prototype.W=function(){var a;var h;var f;var g;this.C=this._;a=e(this,b.a_4,46);if(a===0){return false}this.B=this._;switch(a){case 0:return false;case 1:f=true;a:while(f===true){f=false;h=this.A-this._;g=true;b:while(g===true){g=false;if(!d(this,1,'а')){break b}break a}this._=this.A-h;if(!d(this,1,'я')){return false}}if(!c(this,'')){return false}break;case 2:if(!c(this,'')){return false}break}return true};b.prototype.r_verb=b.prototype.W;function I(a){var f;var i;var g;var h;a.C=a._;f=e(a,b.a_4,46);if(f===0){return false}a.B=a._;switch(f){case 0:return false;case 1:g=true;a:while(g===true){g=false;i=a.A-a._;h=true;b:while(h===true){h=false;if(!d(a,1,'а')){break b}break a}a._=a.A-i;if(!d(a,1,'я')){return false}}if(!c(a,'')){return false}break;case 2:if(!c(a,'')){return false}break}return true};b.prototype.S=function(){var a;this.C=this._;a=e(this,b.a_5,36);if(a===0){return false}this.B=this._;switch(a){case 0:return false;case 1:if(!c(this,'')){return false}break}return true};b.prototype.r_noun=b.prototype.S;function F(a){var d;a.C=a._;d=e(a,b.a_5,36);if(d===0){return false}a.B=a._;switch(d){case 0:return false;case 1:if(!c(a,'')){return false}break}return true};b.prototype.Q=function(){var a;var d;this.C=this._;a=e(this,b.a_6,2);if(a===0){return false}this.B=d=this._;if(!(!(this.I_p2<=d)?false:true)){return false}switch(a){case 0:return false;case 1:if(!c(this,'')){return false}break}return true};b.prototype.r_derivational=b.prototype.Q;function C(a){var d;var f;a.C=a._;d=e(a,b.a_6,2);if(d===0){return false}a.B=f=a._;if(!(!(a.I_p2<=f)?false:true)){return false}switch(d){case 0:return false;case 1:if(!c(a,'')){return false}break}return true};b.prototype.V=function(){var a;this.C=this._;a=e(this,b.a_7,4);if(a===0){return false}this.B=this._;switch(a){case 0:return false;case 1:if(!c(this,'')){return false}this.C=this._;if(!d(this,1,'н')){return false}this.B=this._;if(!d(this,1,'н')){return false}if(!c(this,'')){return false}break;case 2:if(!d(this,1,'н')){return false}if(!c(this,'')){return false}break;case 3:if(!c(this,'')){return false}break}return true};b.prototype.r_tidy_up=b.prototype.V;function y(a){var f;a.C=a._;f=e(a,b.a_7,4);if(f===0){return false}a.B=a._;switch(f){case 0:return false;case 1:if(!c(a,'')){return false}a.C=a._;if(!d(a,1,'н')){return false}a.B=a._;if(!d(a,1,'н')){return false}if(!c(a,'')){return false}break;case 2:if(!d(a,1,'н')){return false}if(!c(a,'')){return false}break;case 3:if(!c(a,'')){return false}break}return true};b.prototype.H=function(){var s;var v;var w;var A;var p;var q;var i;var t;var u;var e;var f;var g;var h;var a;var j;var b;var k;var l;var m;var n;var x;var z;var o;var B;var J;var K;var L;var M;var N;var O;var r;s=this._;e=true;a:while(e===true){e=false;if(!D(this)){break a}}x=this._=s;this.E=x;o=this._=z=this.A;v=z-o;if(o<this.I_pV){return false}K=this._=this.I_pV;w=this.E;this.E=K;M=this._=(L=this.A)-v;A=L-M;f=true;c:while(f===true){f=false;g=true;b:while(g===true){g=false;p=this.A-this._;h=true;a:while(h===true){h=false;if(!E(this)){break a}break b}J=this._=(B=this.A)-p;q=B-J;a=true;a:while(a===true){a=false;if(!H(this)){this._=this.A-q;break a}}j=true;a:while(j===true){j=false;i=this.A-this._;b=true;d:while(b===true){b=false;if(!G(this)){break d}break a}this._=this.A-i;k=true;d:while(k===true){k=false;if(!I(this)){break d}break a}this._=this.A-i;if(!F(this)){break c}}}}O=this._=(N=this.A)-A;t=N-O;l=true;a:while(l===true){l=false;this.C=this._;if(!d(this,1,'и')){this._=this.A-t;break a}this.B=this._;if(!c(this,'')){return false}}u=this.A-this._;m=true;a:while(m===true){m=false;if(!C(this)){break a}}this._=this.A-u;n=true;a:while(n===true){n=false;if(!y(this)){break a}}r=this.E=w;this._=r;return true};b.prototype.stem=b.prototype.H;b.prototype.L=function(a){return a instanceof b};b.prototype.equals=b.prototype.L;b.prototype.M=function(){var c;var a;var b;var d;c='RussianStemmer';a=0;for(b=0;b<c.length;b++){d=c.charCodeAt(b);a=(a<<5)-a+d;a=a&a}return a|0};b.prototype.hashCode=b.prototype.M;b.serialVersionUID=1;f(b,'methodObject',function(){return new b});f(b,'a_0',function(){return[new a('в',-1,1),new a('ив',0,2),new a('ыв',0,2),new a('вши',-1,1),new a('ивши',3,2),new a('ывши',3,2),new a('вшись',-1,1),new a('ившись',6,2),new a('ывшись',6,2)]});f(b,'a_1',function(){return[new a('ее',-1,1),new a('ие',-1,1),new a('ое',-1,1),new a('ые',-1,1),new a('ими',-1,1),new a('ыми',-1,1),new a('ей',-1,1),new a('ий',-1,1),new a('ой',-1,1),new a('ый',-1,1),new a('ем',-1,1),new a('им',-1,1),new a('ом',-1,1),new a('ым',-1,1),new a('его',-1,1),new a('ого',-1,1),new a('ему',-1,1),new a('ому',-1,1),new a('их',-1,1),new a('ых',-1,1),new a('ею',-1,1),new a('ою',-1,1),new a('ую',-1,1),new a('юю',-1,1),new a('ая',-1,1),new a('яя',-1,1)]});f(b,'a_2',function(){return[new a('ем',-1,1),new a('нн',-1,1),new a('вш',-1,1),new a('ивш',2,2),new a('ывш',2,2),new a('щ',-1,1),new a('ющ',5,1),new a('ующ',6,2)]});f(b,'a_3',function(){return[new a('сь',-1,1),new a('ся',-1,1)]});f(b,'a_4',function(){return[new a('ла',-1,1),new a('ила',0,2),new a('ыла',0,2),new a('на',-1,1),new a('ена',3,2),new a('ете',-1,1),new a('ите',-1,2),new a('йте',-1,1),new a('ейте',7,2),new a('уйте',7,2),new a('ли',-1,1),new a('или',10,2),new a('ыли',10,2),new a('й',-1,1),new a('ей',13,2),new a('уй',13,2),new a('л',-1,1),new a('ил',16,2),new a('ыл',16,2),new a('ем',-1,1),new a('им',-1,2),new a('ым',-1,2),new a('н',-1,1),new a('ен',22,2),new a('ло',-1,1),new a('ило',24,2),new a('ыло',24,2),new a('но',-1,1),new a('ено',27,2),new a('нно',27,1),new a('ет',-1,1),new a('ует',30,2),new a('ит',-1,2),new a('ыт',-1,2),new a('ют',-1,1),new a('уют',34,2),new a('ят',-1,2),new a('ны',-1,1),new a('ены',37,2),new a('ть',-1,1),new a('ить',39,2),new a('ыть',39,2),new a('ешь',-1,1),new a('ишь',-1,2),new a('ю',-1,2),new a('ую',44,2)]});f(b,'a_5',function(){return[new a('а',-1,1),new a('ев',-1,1),new a('ов',-1,1),new a('е',-1,1),new a('ие',3,1),new a('ье',3,1),new a('и',-1,1),new a('еи',6,1),new a('ии',6,1),new a('ами',6,1),new a('ями',6,1),new a('иями',10,1),new a('й',-1,1),new a('ей',12,1),new a('ией',13,1),new a('ий',12,1),new a('ой',12,1),new a('ам',-1,1),new a('ем',-1,1),new a('ием',18,1),new a('ом',-1,1),new a('ям',-1,1),new a('иям',21,1),new a('о',-1,1),new a('у',-1,1),new a('ах',-1,1),new a('ях',-1,1),new a('иях',26,1),new a('ы',-1,1),new a('ь',-1,1),new a('ю',-1,1),new a('ию',30,1),new a('ью',30,1),new a('я',-1,1),new a('ия',33,1),new a('ья',33,1)]});f(b,'a_6',function(){return[new a('ост',-1,1),new a('ость',-1,1)]});f(b,'a_7',function(){return[new a('ейше',-1,1),new a('н',-1,2),new a('ейш',-1,1),new a('ь',-1,3)]});f(b,'g_v',function(){return[33,65,8,232]});var o={'src/stemmer.jsx':{Stemmer:m},'src/russian-stemmer.jsx':{RussianStemmer:b}}}(JSX))
var Stemmer = JSX.require("src/russian-stemmer.jsx").RussianStemmer;
"""


class SearchRussian(SearchLanguage):
    lang = 'ru'
    language_name = 'Russian'
    js_stemmer_rawcode = 'russian-stemmer.js'
    js_stemmer_code = js_stemmer
    stopwords = russian_stopwords

    def init(self, options):
        # type: (Any) -> None
        self.stemmer = snowballstemmer.stemmer('russian')

    def stem(self, word):
        # type: (unicode) -> unicode
        return self.stemmer.stemWord(word.lower())
