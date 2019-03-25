// generatedy by JSX compiler 0.9.89 (2014-05-20 06:01:03 +0900; 8e8c6105f36f3dfe440ea026a3c93a3444977102)
var JSX = {};
(function (JSX) {
/**
 * extends the class
 */
function $__jsx_extend(derivations, base) {
	var ctor = function () {};
	ctor.prototype = base.prototype;
	var proto = new ctor();
	for (var i in derivations) {
		derivations[i].prototype = proto;
	}
}

/**
 * copies the implementations from source interface to target
 */
function $__jsx_merge_interface(target, source) {
	for (var k in source.prototype)
		if (source.prototype.hasOwnProperty(k))
			target.prototype[k] = source.prototype[k];
}

/**
 * defers the initialization of the property
 */
function $__jsx_lazy_init(obj, prop, func) {
	function reset(obj, prop, value) {
		delete obj[prop];
		obj[prop] = value;
		return value;
	}

	Object.defineProperty(obj, prop, {
		get: function () {
			return reset(obj, prop, func());
		},
		set: function (v) {
			reset(obj, prop, v);
		},
		enumerable: true,
		configurable: true
	});
}

var $__jsx_imul = Math.imul;
if (typeof $__jsx_imul === "undefined") {
	$__jsx_imul = function (a, b) {
		var ah  = (a >>> 16) & 0xffff;
		var al = a & 0xffff;
		var bh  = (b >>> 16) & 0xffff;
		var bl = b & 0xffff;
		return ((al * bl) + (((ah * bl + al * bh) << 16) >>> 0)|0);
	};
}

/**
 * fused int-ops with side-effects
 */
function $__jsx_ipadd(o, p, r) {
	return o[p] = (o[p] + r) | 0;
}
function $__jsx_ipsub(o, p, r) {
	return o[p] = (o[p] - r) | 0;
}
function $__jsx_ipmul(o, p, r) {
	return o[p] = $__jsx_imul(o[p], r);
}
function $__jsx_ipdiv(o, p, r) {
	return o[p] = (o[p] / r) | 0;
}
function $__jsx_ipmod(o, p, r) {
	return o[p] = (o[p] % r) | 0;
}
function $__jsx_ippostinc(o, p) {
	var v = o[p];
	o[p] = (v + 1) | 0;
	return v;
}
function $__jsx_ippostdec(o, p) {
	var v = o[p];
	o[p] = (v - 1) | 0;
	return v;
}

/**
 * non-inlined version of Array#each
 */
function $__jsx_forEach(o, f) {
	var l = o.length;
	for (var i = 0; i < l; ++i)
		f(o[i]);
}

/*
 * global functions, renamed to avoid conflict with local variable names
 */
var $__jsx_parseInt = parseInt;
var $__jsx_parseFloat = parseFloat;
function $__jsx_isNaN(n) { return n !== n; }
var $__jsx_isFinite = isFinite;

var $__jsx_encodeURIComponent = encodeURIComponent;
var $__jsx_decodeURIComponent = decodeURIComponent;
var $__jsx_encodeURI = encodeURI;
var $__jsx_decodeURI = decodeURI;

var $__jsx_ObjectToString = Object.prototype.toString;
var $__jsx_ObjectHasOwnProperty = Object.prototype.hasOwnProperty;

/*
 * profiler object, initialized afterwards
 */
function $__jsx_profiler() {
}

/*
 * public interface to JSX code
 */
JSX.require = function (path) {
	var m = $__jsx_classMap[path];
	return m !== undefined ? m : null;
};

JSX.profilerIsRunning = function () {
	return $__jsx_profiler.getResults != null;
};

JSX.getProfileResults = function () {
	return ($__jsx_profiler.getResults || function () { return {}; })();
};

JSX.postProfileResults = function (url, cb) {
	if ($__jsx_profiler.postResults == null)
		throw new Error("profiler has not been turned on");
	return $__jsx_profiler.postResults(url, cb);
};

JSX.resetProfileResults = function () {
	if ($__jsx_profiler.resetResults == null)
		throw new Error("profiler has not been turned on");
	return $__jsx_profiler.resetResults();
};
JSX.DEBUG = false;
var GeneratorFunction$0 = 
(function () {
  try {
    return Function('import {GeneratorFunction} from "std:iteration"; return GeneratorFunction')();
  } catch (e) {
    return function GeneratorFunction () {};
  }
})();
var __jsx_generator_object$0 = 
(function () {
  function __jsx_generator_object() {
  	this.__next = 0;
  	this.__loop = null;
	this.__seed = null;
  	this.__value = undefined;
  	this.__status = 0;	// SUSPENDED: 0, ACTIVE: 1, DEAD: 2
  }

  __jsx_generator_object.prototype.next = function (seed) {
  	switch (this.__status) {
  	case 0:
  		this.__status = 1;
  		this.__seed = seed;

  		// go next!
  		this.__loop(this.__next);

  		var done = false;
  		if (this.__next != -1) {
  			this.__status = 0;
  		} else {
  			this.__status = 2;
  			done = true;
  		}
  		return { value: this.__value, done: done };
  	case 1:
  		throw new Error("Generator is already running");
  	case 2:
  		throw new Error("Generator is already finished");
  	default:
  		throw new Error("Unexpected generator internal state");
  	}
  };

  return __jsx_generator_object;
}());
function Among(s, substring_i, result) {
	this.s_size = s.length;
	this.s = s;
	this.substring_i = substring_i;
	this.result = result;
	this.method = null;
	this.instance = null;
};

function Among$0(s, substring_i, result, method, instance) {
	this.s_size = s.length;
	this.s = s;
	this.substring_i = substring_i;
	this.result = result;
	this.method = method;
	this.instance = instance;
};

$__jsx_extend([Among, Among$0], Object);
function Stemmer() {
};

$__jsx_extend([Stemmer], Object);
function BaseStemmer() {
	var current$0;
	var cursor$0;
	var limit$0;
	this.cache = ({  });
	current$0 = this.current = "";
	cursor$0 = this.cursor = 0;
	limit$0 = this.limit = current$0.length;
	this.limit_backward = 0;
	this.bra = cursor$0;
	this.ket = limit$0;
};

$__jsx_extend([BaseStemmer], Stemmer);
BaseStemmer.prototype.setCurrent$S = function (value) {
	var current$0;
	var cursor$0;
	var limit$0;
	current$0 = this.current = value;
	cursor$0 = this.cursor = 0;
	limit$0 = this.limit = current$0.length;
	this.limit_backward = 0;
	this.bra = cursor$0;
	this.ket = limit$0;
};


function BaseStemmer$setCurrent$LBaseStemmer$S($this, value) {
	var current$0;
	var cursor$0;
	var limit$0;
	current$0 = $this.current = value;
	cursor$0 = $this.cursor = 0;
	limit$0 = $this.limit = current$0.length;
	$this.limit_backward = 0;
	$this.bra = cursor$0;
	$this.ket = limit$0;
};

BaseStemmer.setCurrent$LBaseStemmer$S = BaseStemmer$setCurrent$LBaseStemmer$S;

BaseStemmer.prototype.getCurrent$ = function () {
	return this.current;
};


function BaseStemmer$getCurrent$LBaseStemmer$($this) {
	return $this.current;
};

BaseStemmer.getCurrent$LBaseStemmer$ = BaseStemmer$getCurrent$LBaseStemmer$;

BaseStemmer.prototype.copy_from$LBaseStemmer$ = function (other) {
	this.current = other.current;
	this.cursor = other.cursor;
	this.limit = other.limit;
	this.limit_backward = other.limit_backward;
	this.bra = other.bra;
	this.ket = other.ket;
};


function BaseStemmer$copy_from$LBaseStemmer$LBaseStemmer$($this, other) {
	$this.current = other.current;
	$this.cursor = other.cursor;
	$this.limit = other.limit;
	$this.limit_backward = other.limit_backward;
	$this.bra = other.bra;
	$this.ket = other.ket;
};

BaseStemmer.copy_from$LBaseStemmer$LBaseStemmer$ = BaseStemmer$copy_from$LBaseStemmer$LBaseStemmer$;

BaseStemmer.prototype.in_grouping$AIII = function (s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor >= this.limit) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor);
	if (ch > max || ch < min) {
		return false;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$in_grouping$LBaseStemmer$AIII($this, s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor >= $this.limit) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor);
	if (ch > max || ch < min) {
		return false;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.in_grouping$LBaseStemmer$AIII = BaseStemmer$in_grouping$LBaseStemmer$AIII;

BaseStemmer.prototype.in_grouping_b$AIII = function (s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor <= this.limit_backward) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor - 1);
	if (ch > max || ch < min) {
		return false;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor <= $this.limit_backward) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor - 1);
	if (ch > max || ch < min) {
		return false;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.in_grouping_b$LBaseStemmer$AIII = BaseStemmer$in_grouping_b$LBaseStemmer$AIII;

BaseStemmer.prototype.out_grouping$AIII = function (s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor >= this.limit) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor);
	if (ch > max || ch < min) {
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		return true;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0X1 << (ch & 0x7)) === 0) {
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		return true;
	}
	return false;
};


function BaseStemmer$out_grouping$LBaseStemmer$AIII($this, s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor >= $this.limit) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor);
	if (ch > max || ch < min) {
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		return true;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0X1 << (ch & 0x7)) === 0) {
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		return true;
	}
	return false;
};

BaseStemmer.out_grouping$LBaseStemmer$AIII = BaseStemmer$out_grouping$LBaseStemmer$AIII;

BaseStemmer.prototype.out_grouping_b$AIII = function (s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor <= this.limit_backward) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor - 1);
	if (ch > max || ch < min) {
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		return true;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		return true;
	}
	return false;
};


function BaseStemmer$out_grouping_b$LBaseStemmer$AIII($this, s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor <= $this.limit_backward) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor - 1);
	if (ch > max || ch < min) {
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		return true;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		return true;
	}
	return false;
};

BaseStemmer.out_grouping_b$LBaseStemmer$AIII = BaseStemmer$out_grouping_b$LBaseStemmer$AIII;

BaseStemmer.prototype.in_range$II = function (min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor >= this.limit) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor);
	if (ch > max || ch < min) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$in_range$LBaseStemmer$II($this, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor >= $this.limit) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor);
	if (ch > max || ch < min) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.in_range$LBaseStemmer$II = BaseStemmer$in_range$LBaseStemmer$II;

BaseStemmer.prototype.in_range_b$II = function (min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor <= this.limit_backward) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor - 1);
	if (ch > max || ch < min) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$in_range_b$LBaseStemmer$II($this, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor <= $this.limit_backward) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor - 1);
	if (ch > max || ch < min) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.in_range_b$LBaseStemmer$II = BaseStemmer$in_range_b$LBaseStemmer$II;

BaseStemmer.prototype.out_range$II = function (min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor >= this.limit) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor);
	if (! (ch > max || ch < min)) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$out_range$LBaseStemmer$II($this, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor >= $this.limit) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor);
	if (! (ch > max || ch < min)) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.out_range$LBaseStemmer$II = BaseStemmer$out_range$LBaseStemmer$II;

BaseStemmer.prototype.out_range_b$II = function (min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor <= this.limit_backward) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor - 1);
	if (! (ch > max || ch < min)) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$out_range_b$LBaseStemmer$II($this, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor <= $this.limit_backward) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor - 1);
	if (! (ch > max || ch < min)) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.out_range_b$LBaseStemmer$II = BaseStemmer$out_range_b$LBaseStemmer$II;

BaseStemmer.prototype.eq_s$IS = function (s_size, s) {
	var cursor$0;
	if (((this.limit - this.cursor) | 0) < s_size) {
		return false;
	}
	if (this.current.slice(cursor$0 = this.cursor, ((cursor$0 + s_size) | 0)) !== s) {
		return false;
	}
	this.cursor = (this.cursor + s_size) | 0;
	return true;
};


function BaseStemmer$eq_s$LBaseStemmer$IS($this, s_size, s) {
	var cursor$0;
	if ((($this.limit - $this.cursor) | 0) < s_size) {
		return false;
	}
	if ($this.current.slice(cursor$0 = $this.cursor, ((cursor$0 + s_size) | 0)) !== s) {
		return false;
	}
	$this.cursor = ($this.cursor + s_size) | 0;
	return true;
};

BaseStemmer.eq_s$LBaseStemmer$IS = BaseStemmer$eq_s$LBaseStemmer$IS;

BaseStemmer.prototype.eq_s_b$IS = function (s_size, s) {
	var cursor$0;
	if (((this.cursor - this.limit_backward) | 0) < s_size) {
		return false;
	}
	if (this.current.slice((((cursor$0 = this.cursor) - s_size) | 0), cursor$0) !== s) {
		return false;
	}
	this.cursor = (this.cursor - s_size) | 0;
	return true;
};


function BaseStemmer$eq_s_b$LBaseStemmer$IS($this, s_size, s) {
	var cursor$0;
	if ((($this.cursor - $this.limit_backward) | 0) < s_size) {
		return false;
	}
	if ($this.current.slice((((cursor$0 = $this.cursor) - s_size) | 0), cursor$0) !== s) {
		return false;
	}
	$this.cursor = ($this.cursor - s_size) | 0;
	return true;
};

BaseStemmer.eq_s_b$LBaseStemmer$IS = BaseStemmer$eq_s_b$LBaseStemmer$IS;

BaseStemmer.prototype.eq_v$S = function (s) {
	return BaseStemmer$eq_s$LBaseStemmer$IS(this, s.length, s);
};


function BaseStemmer$eq_v$LBaseStemmer$S($this, s) {
	return BaseStemmer$eq_s$LBaseStemmer$IS($this, s.length, s);
};

BaseStemmer.eq_v$LBaseStemmer$S = BaseStemmer$eq_v$LBaseStemmer$S;

BaseStemmer.prototype.eq_v_b$S = function (s) {
	return BaseStemmer$eq_s_b$LBaseStemmer$IS(this, s.length, s);
};


function BaseStemmer$eq_v_b$LBaseStemmer$S($this, s) {
	return BaseStemmer$eq_s_b$LBaseStemmer$IS($this, s.length, s);
};

BaseStemmer.eq_v_b$LBaseStemmer$S = BaseStemmer$eq_v_b$LBaseStemmer$S;

BaseStemmer.prototype.find_among$ALAmong$I = function (v, v_size) {
	var i;
	var j;
	var c;
	var l;
	var common_i;
	var common_j;
	var first_key_inspected;
	var k;
	var diff;
	var common;
	var w;
	var i2;
	var res;
	i = 0;
	j = v_size;
	c = this.cursor;
	l = this.limit;
	common_i = 0;
	common_j = 0;
	first_key_inspected = false;
	while (true) {
		k = i + (j - i >>> 1);
		diff = 0;
		common = (common_i < common_j ? common_i : common_j);
		w = v[k];
		for (i2 = common; i2 < w.s_size; i2++) {
			if (c + common === l) {
				diff = -1;
				break;
			}
			diff = this.current.charCodeAt(c + common) - w.s.charCodeAt(i2);
			if (diff !== 0) {
				break;
			}
			common++;
		}
		if (diff < 0) {
			j = k;
			common_j = common;
		} else {
			i = k;
			common_i = common;
		}
		if (j - i <= 1) {
			if (i > 0) {
				break;
			}
			if (j === i) {
				break;
			}
			if (first_key_inspected) {
				break;
			}
			first_key_inspected = true;
		}
	}
	while (true) {
		w = v[i];
		if (common_i >= w.s_size) {
			this.cursor = (c + w.s_size | 0);
			if (w.method == null) {
				return w.result;
			}
			res = w.method(w.instance);
			this.cursor = (c + w.s_size | 0);
			if (res) {
				return w.result;
			}
		}
		i = w.substring_i;
		if (i < 0) {
			return 0;
		}
	}
	return -1;
};


function BaseStemmer$find_among$LBaseStemmer$ALAmong$I($this, v, v_size) {
	var i;
	var j;
	var c;
	var l;
	var common_i;
	var common_j;
	var first_key_inspected;
	var k;
	var diff;
	var common;
	var w;
	var i2;
	var res;
	i = 0;
	j = v_size;
	c = $this.cursor;
	l = $this.limit;
	common_i = 0;
	common_j = 0;
	first_key_inspected = false;
	while (true) {
		k = i + (j - i >>> 1);
		diff = 0;
		common = (common_i < common_j ? common_i : common_j);
		w = v[k];
		for (i2 = common; i2 < w.s_size; i2++) {
			if (c + common === l) {
				diff = -1;
				break;
			}
			diff = $this.current.charCodeAt(c + common) - w.s.charCodeAt(i2);
			if (diff !== 0) {
				break;
			}
			common++;
		}
		if (diff < 0) {
			j = k;
			common_j = common;
		} else {
			i = k;
			common_i = common;
		}
		if (j - i <= 1) {
			if (i > 0) {
				break;
			}
			if (j === i) {
				break;
			}
			if (first_key_inspected) {
				break;
			}
			first_key_inspected = true;
		}
	}
	while (true) {
		w = v[i];
		if (common_i >= w.s_size) {
			$this.cursor = (c + w.s_size | 0);
			if (w.method == null) {
				return w.result;
			}
			res = w.method(w.instance);
			$this.cursor = (c + w.s_size | 0);
			if (res) {
				return w.result;
			}
		}
		i = w.substring_i;
		if (i < 0) {
			return 0;
		}
	}
	return -1;
};

BaseStemmer.find_among$LBaseStemmer$ALAmong$I = BaseStemmer$find_among$LBaseStemmer$ALAmong$I;

BaseStemmer.prototype.find_among_b$ALAmong$I = function (v, v_size) {
	var i;
	var j;
	var c;
	var lb;
	var common_i;
	var common_j;
	var first_key_inspected;
	var k;
	var diff;
	var common;
	var w;
	var i2;
	var res;
	i = 0;
	j = v_size;
	c = this.cursor;
	lb = this.limit_backward;
	common_i = 0;
	common_j = 0;
	first_key_inspected = false;
	while (true) {
		k = i + (j - i >> 1);
		diff = 0;
		common = (common_i < common_j ? common_i : common_j);
		w = v[k];
		for (i2 = w.s_size - 1 - common; i2 >= 0; i2--) {
			if (c - common === lb) {
				diff = -1;
				break;
			}
			diff = this.current.charCodeAt(c - 1 - common) - w.s.charCodeAt(i2);
			if (diff !== 0) {
				break;
			}
			common++;
		}
		if (diff < 0) {
			j = k;
			common_j = common;
		} else {
			i = k;
			common_i = common;
		}
		if (j - i <= 1) {
			if (i > 0) {
				break;
			}
			if (j === i) {
				break;
			}
			if (first_key_inspected) {
				break;
			}
			first_key_inspected = true;
		}
	}
	while (true) {
		w = v[i];
		if (common_i >= w.s_size) {
			this.cursor = (c - w.s_size | 0);
			if (w.method == null) {
				return w.result;
			}
			res = w.method(this);
			this.cursor = (c - w.s_size | 0);
			if (res) {
				return w.result;
			}
		}
		i = w.substring_i;
		if (i < 0) {
			return 0;
		}
	}
	return -1;
};


function BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, v, v_size) {
	var i;
	var j;
	var c;
	var lb;
	var common_i;
	var common_j;
	var first_key_inspected;
	var k;
	var diff;
	var common;
	var w;
	var i2;
	var res;
	i = 0;
	j = v_size;
	c = $this.cursor;
	lb = $this.limit_backward;
	common_i = 0;
	common_j = 0;
	first_key_inspected = false;
	while (true) {
		k = i + (j - i >> 1);
		diff = 0;
		common = (common_i < common_j ? common_i : common_j);
		w = v[k];
		for (i2 = w.s_size - 1 - common; i2 >= 0; i2--) {
			if (c - common === lb) {
				diff = -1;
				break;
			}
			diff = $this.current.charCodeAt(c - 1 - common) - w.s.charCodeAt(i2);
			if (diff !== 0) {
				break;
			}
			common++;
		}
		if (diff < 0) {
			j = k;
			common_j = common;
		} else {
			i = k;
			common_i = common;
		}
		if (j - i <= 1) {
			if (i > 0) {
				break;
			}
			if (j === i) {
				break;
			}
			if (first_key_inspected) {
				break;
			}
			first_key_inspected = true;
		}
	}
	while (true) {
		w = v[i];
		if (common_i >= w.s_size) {
			$this.cursor = (c - w.s_size | 0);
			if (w.method == null) {
				return w.result;
			}
			res = w.method($this);
			$this.cursor = (c - w.s_size | 0);
			if (res) {
				return w.result;
			}
		}
		i = w.substring_i;
		if (i < 0) {
			return 0;
		}
	}
	return -1;
};

BaseStemmer.find_among_b$LBaseStemmer$ALAmong$I = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I;

BaseStemmer.prototype.replace_s$IIS = function (c_bra, c_ket, s) {
	var adjustment;
	adjustment = ((s.length - (((c_ket - c_bra) | 0))) | 0);
	this.current = this.current.slice(0, c_bra) + s + this.current.slice(c_ket);
	this.limit = (this.limit + adjustment) | 0;
	if (this.cursor >= c_ket) {
		this.cursor = (this.cursor + adjustment) | 0;
	} else if (this.cursor > c_bra) {
		this.cursor = c_bra;
	}
	return (adjustment | 0);
};


function BaseStemmer$replace_s$LBaseStemmer$IIS($this, c_bra, c_ket, s) {
	var adjustment;
	adjustment = ((s.length - (((c_ket - c_bra) | 0))) | 0);
	$this.current = $this.current.slice(0, c_bra) + s + $this.current.slice(c_ket);
	$this.limit = ($this.limit + adjustment) | 0;
	if ($this.cursor >= c_ket) {
		$this.cursor = ($this.cursor + adjustment) | 0;
	} else if ($this.cursor > c_bra) {
		$this.cursor = c_bra;
	}
	return (adjustment | 0);
};

BaseStemmer.replace_s$LBaseStemmer$IIS = BaseStemmer$replace_s$LBaseStemmer$IIS;

BaseStemmer.prototype.slice_check$ = function () {
	var bra$0;
	var ket$0;
	var limit$0;
	return ((bra$0 = this.bra) < 0 || bra$0 > (ket$0 = this.ket) || ket$0 > (limit$0 = this.limit) || limit$0 > this.current.length ? false : true);
};


function BaseStemmer$slice_check$LBaseStemmer$($this) {
	var bra$0;
	var ket$0;
	var limit$0;
	return ((bra$0 = $this.bra) < 0 || bra$0 > (ket$0 = $this.ket) || ket$0 > (limit$0 = $this.limit) || limit$0 > $this.current.length ? false : true);
};

BaseStemmer.slice_check$LBaseStemmer$ = BaseStemmer$slice_check$LBaseStemmer$;

BaseStemmer.prototype.slice_from$S = function (s) {
	var result;
	var bra$0;
	var ket$0;
	var limit$0;
	result = false;
	if ((bra$0 = this.bra) < 0 || bra$0 > (ket$0 = this.ket) || ket$0 > (limit$0 = this.limit) || limit$0 > this.current.length ? false : true) {
		BaseStemmer$replace_s$LBaseStemmer$IIS(this, this.bra, this.ket, s);
		result = true;
	}
	return result;
};


function BaseStemmer$slice_from$LBaseStemmer$S($this, s) {
	var result;
	var bra$0;
	var ket$0;
	var limit$0;
	result = false;
	if ((bra$0 = $this.bra) < 0 || bra$0 > (ket$0 = $this.ket) || ket$0 > (limit$0 = $this.limit) || limit$0 > $this.current.length ? false : true) {
		BaseStemmer$replace_s$LBaseStemmer$IIS($this, $this.bra, $this.ket, s);
		result = true;
	}
	return result;
};

BaseStemmer.slice_from$LBaseStemmer$S = BaseStemmer$slice_from$LBaseStemmer$S;

BaseStemmer.prototype.slice_del$ = function () {
	return BaseStemmer$slice_from$LBaseStemmer$S(this, "");
};


function BaseStemmer$slice_del$LBaseStemmer$($this) {
	return BaseStemmer$slice_from$LBaseStemmer$S($this, "");
};

BaseStemmer.slice_del$LBaseStemmer$ = BaseStemmer$slice_del$LBaseStemmer$;

BaseStemmer.prototype.insert$IIS = function (c_bra, c_ket, s) {
	var adjustment;
	adjustment = BaseStemmer$replace_s$LBaseStemmer$IIS(this, c_bra, c_ket, s);
	if (c_bra <= this.bra) {
		this.bra = (this.bra + adjustment) | 0;
	}
	if (c_bra <= this.ket) {
		this.ket = (this.ket + adjustment) | 0;
	}
};


function BaseStemmer$insert$LBaseStemmer$IIS($this, c_bra, c_ket, s) {
	var adjustment;
	adjustment = BaseStemmer$replace_s$LBaseStemmer$IIS($this, c_bra, c_ket, s);
	if (c_bra <= $this.bra) {
		$this.bra = ($this.bra + adjustment) | 0;
	}
	if (c_bra <= $this.ket) {
		$this.ket = ($this.ket + adjustment) | 0;
	}
};

BaseStemmer.insert$LBaseStemmer$IIS = BaseStemmer$insert$LBaseStemmer$IIS;

BaseStemmer.prototype.slice_to$S = function (s) {
	var result;
	var bra$0;
	var ket$0;
	var limit$0;
	result = '';
	if ((bra$0 = this.bra) < 0 || bra$0 > (ket$0 = this.ket) || ket$0 > (limit$0 = this.limit) || limit$0 > this.current.length ? false : true) {
		result = this.current.slice(this.bra, this.ket);
	}
	return result;
};


function BaseStemmer$slice_to$LBaseStemmer$S($this, s) {
	var result;
	var bra$0;
	var ket$0;
	var limit$0;
	result = '';
	if ((bra$0 = $this.bra) < 0 || bra$0 > (ket$0 = $this.ket) || ket$0 > (limit$0 = $this.limit) || limit$0 > $this.current.length ? false : true) {
		result = $this.current.slice($this.bra, $this.ket);
	}
	return result;
};

BaseStemmer.slice_to$LBaseStemmer$S = BaseStemmer$slice_to$LBaseStemmer$S;

BaseStemmer.prototype.assign_to$S = function (s) {
	return this.current.slice(0, this.limit);
};


function BaseStemmer$assign_to$LBaseStemmer$S($this, s) {
	return $this.current.slice(0, $this.limit);
};

BaseStemmer.assign_to$LBaseStemmer$S = BaseStemmer$assign_to$LBaseStemmer$S;

BaseStemmer.prototype.stem$ = function () {
	return false;
};


BaseStemmer.prototype.stemWord$S = function (word) {
	var result;
	var current$0;
	var cursor$0;
	var limit$0;
	result = this.cache['.' + word];
	if (result == null) {
		current$0 = this.current = word;
		cursor$0 = this.cursor = 0;
		limit$0 = this.limit = current$0.length;
		this.limit_backward = 0;
		this.bra = cursor$0;
		this.ket = limit$0;
		this.stem$();
		result = this.current;
		this.cache['.' + word] = result;
	}
	return result;
};

BaseStemmer.prototype.stemWord = BaseStemmer.prototype.stemWord$S;

BaseStemmer.prototype.stemWords$AS = function (words) {
	var results;
	var i;
	var word;
	var result;
	var current$0;
	var cursor$0;
	var limit$0;
	results = [  ];
	for (i = 0; i < words.length; i++) {
		word = words[i];
		result = this.cache['.' + word];
		if (result == null) {
			current$0 = this.current = word;
			cursor$0 = this.cursor = 0;
			limit$0 = this.limit = current$0.length;
			this.limit_backward = 0;
			this.bra = cursor$0;
			this.ket = limit$0;
			this.stem$();
			result = this.current;
			this.cache['.' + word] = result;
		}
		results.push(result);
	}
	return results;
};

BaseStemmer.prototype.stemWords = BaseStemmer.prototype.stemWords$AS;

function PortugueseStemmer() {
	BaseStemmer.call(this);
	this.I_p2 = 0;
	this.I_p1 = 0;
	this.I_pV = 0;
};

$__jsx_extend([PortugueseStemmer], BaseStemmer);
PortugueseStemmer.prototype.copy_from$LPortugueseStemmer$ = function (other) {
	this.I_p2 = other.I_p2;
	this.I_p1 = other.I_p1;
	this.I_pV = other.I_pV;
	BaseStemmer$copy_from$LBaseStemmer$LBaseStemmer$(this, other);
};

PortugueseStemmer.prototype.copy_from = PortugueseStemmer.prototype.copy_from$LPortugueseStemmer$;

PortugueseStemmer.prototype.r_prelude$ = function () {
	var among_var;
	var v_1;
	var lab1;
	var $__jsx_postinc_t;
replab0:
	while (true) {
		v_1 = this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			this.bra = this.cursor;
			among_var = BaseStemmer$find_among$LBaseStemmer$ALAmong$I(this, PortugueseStemmer.a_0, 3);
			if (among_var === 0) {
				break lab1;
			}
			this.ket = this.cursor;
			switch (among_var) {
			case 0:
				break lab1;
			case 1:
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a~")) {
					return false;
				}
				break;
			case 2:
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "o~")) {
					return false;
				}
				break;
			case 3:
				if (this.cursor >= this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
				break;
			}
			continue replab0;
		}
		this.cursor = v_1;
		break replab0;
	}
	return true;
};

PortugueseStemmer.prototype.r_prelude = PortugueseStemmer.prototype.r_prelude$;

function PortugueseStemmer$r_prelude$LPortugueseStemmer$($this) {
	var among_var;
	var v_1;
	var lab1;
	var $__jsx_postinc_t;
replab0:
	while (true) {
		v_1 = $this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			$this.bra = $this.cursor;
			among_var = BaseStemmer$find_among$LBaseStemmer$ALAmong$I($this, PortugueseStemmer.a_0, 3);
			if (among_var === 0) {
				break lab1;
			}
			$this.ket = $this.cursor;
			switch (among_var) {
			case 0:
				break lab1;
			case 1:
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a~")) {
					return false;
				}
				break;
			case 2:
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "o~")) {
					return false;
				}
				break;
			case 3:
				if ($this.cursor >= $this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
				break;
			}
			continue replab0;
		}
		$this.cursor = v_1;
		break replab0;
	}
	return true;
};

PortugueseStemmer.r_prelude$LPortugueseStemmer$ = PortugueseStemmer$r_prelude$LPortugueseStemmer$;

PortugueseStemmer.prototype.r_mark_regions$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_6;
	var v_8;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var lab4;
	var lab6;
	var lab8;
	var lab9;
	var lab10;
	var lab12;
	var lab13;
	var lab15;
	var lab17;
	var lab19;
	var lab21;
	var limit$0;
	var cursor$0;
	var $__jsx_postinc_t;
	this.I_pV = limit$0 = this.limit;
	this.I_p1 = limit$0;
	this.I_p2 = limit$0;
	v_1 = this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_2 = this.cursor;
			lab2 = true;
		lab2:
			while (lab2 === true) {
				lab2 = false;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, PortugueseStemmer.g_v, 97, 250)) {
					break lab2;
				}
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					v_3 = this.cursor;
					lab4 = true;
				lab4:
					while (lab4 === true) {
						lab4 = false;
						if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, PortugueseStemmer.g_v, 97, 250)) {
							break lab4;
						}
					golab5:
						while (true) {
							lab6 = true;
						lab6:
							while (lab6 === true) {
								lab6 = false;
								if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, PortugueseStemmer.g_v, 97, 250)) {
									break lab6;
								}
								break golab5;
							}
							if (this.cursor >= this.limit) {
								break lab4;
							}
							($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
						}
						break lab3;
					}
					this.cursor = v_3;
					if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, PortugueseStemmer.g_v, 97, 250)) {
						break lab2;
					}
				golab7:
					while (true) {
						lab8 = true;
					lab8:
						while (lab8 === true) {
							lab8 = false;
							if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, PortugueseStemmer.g_v, 97, 250)) {
								break lab8;
							}
							break golab7;
						}
						if (this.cursor >= this.limit) {
							break lab2;
						}
						($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
					}
				}
				break lab1;
			}
			this.cursor = v_2;
			if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, PortugueseStemmer.g_v, 97, 250)) {
				break lab0;
			}
			lab9 = true;
		lab9:
			while (lab9 === true) {
				lab9 = false;
				v_6 = this.cursor;
				lab10 = true;
			lab10:
				while (lab10 === true) {
					lab10 = false;
					if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, PortugueseStemmer.g_v, 97, 250)) {
						break lab10;
					}
				golab11:
					while (true) {
						lab12 = true;
					lab12:
						while (lab12 === true) {
							lab12 = false;
							if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, PortugueseStemmer.g_v, 97, 250)) {
								break lab12;
							}
							break golab11;
						}
						if (this.cursor >= this.limit) {
							break lab10;
						}
						($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
					}
					break lab9;
				}
				this.cursor = v_6;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, PortugueseStemmer.g_v, 97, 250)) {
					break lab0;
				}
				if (this.cursor >= this.limit) {
					break lab0;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
		}
		this.I_pV = this.cursor;
	}
	cursor$0 = this.cursor = v_1;
	v_8 = cursor$0;
	lab13 = true;
lab13:
	while (lab13 === true) {
		lab13 = false;
	golab14:
		while (true) {
			lab15 = true;
		lab15:
			while (lab15 === true) {
				lab15 = false;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, PortugueseStemmer.g_v, 97, 250)) {
					break lab15;
				}
				break golab14;
			}
			if (this.cursor >= this.limit) {
				break lab13;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
	golab16:
		while (true) {
			lab17 = true;
		lab17:
			while (lab17 === true) {
				lab17 = false;
				if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, PortugueseStemmer.g_v, 97, 250)) {
					break lab17;
				}
				break golab16;
			}
			if (this.cursor >= this.limit) {
				break lab13;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
		this.I_p1 = this.cursor;
	golab18:
		while (true) {
			lab19 = true;
		lab19:
			while (lab19 === true) {
				lab19 = false;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, PortugueseStemmer.g_v, 97, 250)) {
					break lab19;
				}
				break golab18;
			}
			if (this.cursor >= this.limit) {
				break lab13;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
	golab20:
		while (true) {
			lab21 = true;
		lab21:
			while (lab21 === true) {
				lab21 = false;
				if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, PortugueseStemmer.g_v, 97, 250)) {
					break lab21;
				}
				break golab20;
			}
			if (this.cursor >= this.limit) {
				break lab13;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
		this.I_p2 = this.cursor;
	}
	this.cursor = v_8;
	return true;
};

PortugueseStemmer.prototype.r_mark_regions = PortugueseStemmer.prototype.r_mark_regions$;

function PortugueseStemmer$r_mark_regions$LPortugueseStemmer$($this) {
	var v_1;
	var v_2;
	var v_3;
	var v_6;
	var v_8;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var lab4;
	var lab6;
	var lab8;
	var lab9;
	var lab10;
	var lab12;
	var lab13;
	var lab15;
	var lab17;
	var lab19;
	var lab21;
	var limit$0;
	var cursor$0;
	var $__jsx_postinc_t;
	$this.I_pV = limit$0 = $this.limit;
	$this.I_p1 = limit$0;
	$this.I_p2 = limit$0;
	v_1 = $this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_2 = $this.cursor;
			lab2 = true;
		lab2:
			while (lab2 === true) {
				lab2 = false;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, PortugueseStemmer.g_v, 97, 250)) {
					break lab2;
				}
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					v_3 = $this.cursor;
					lab4 = true;
				lab4:
					while (lab4 === true) {
						lab4 = false;
						if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, PortugueseStemmer.g_v, 97, 250)) {
							break lab4;
						}
					golab5:
						while (true) {
							lab6 = true;
						lab6:
							while (lab6 === true) {
								lab6 = false;
								if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, PortugueseStemmer.g_v, 97, 250)) {
									break lab6;
								}
								break golab5;
							}
							if ($this.cursor >= $this.limit) {
								break lab4;
							}
							($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
						}
						break lab3;
					}
					$this.cursor = v_3;
					if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, PortugueseStemmer.g_v, 97, 250)) {
						break lab2;
					}
				golab7:
					while (true) {
						lab8 = true;
					lab8:
						while (lab8 === true) {
							lab8 = false;
							if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, PortugueseStemmer.g_v, 97, 250)) {
								break lab8;
							}
							break golab7;
						}
						if ($this.cursor >= $this.limit) {
							break lab2;
						}
						($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
					}
				}
				break lab1;
			}
			$this.cursor = v_2;
			if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, PortugueseStemmer.g_v, 97, 250)) {
				break lab0;
			}
			lab9 = true;
		lab9:
			while (lab9 === true) {
				lab9 = false;
				v_6 = $this.cursor;
				lab10 = true;
			lab10:
				while (lab10 === true) {
					lab10 = false;
					if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, PortugueseStemmer.g_v, 97, 250)) {
						break lab10;
					}
				golab11:
					while (true) {
						lab12 = true;
					lab12:
						while (lab12 === true) {
							lab12 = false;
							if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, PortugueseStemmer.g_v, 97, 250)) {
								break lab12;
							}
							break golab11;
						}
						if ($this.cursor >= $this.limit) {
							break lab10;
						}
						($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
					}
					break lab9;
				}
				$this.cursor = v_6;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, PortugueseStemmer.g_v, 97, 250)) {
					break lab0;
				}
				if ($this.cursor >= $this.limit) {
					break lab0;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
		}
		$this.I_pV = $this.cursor;
	}
	cursor$0 = $this.cursor = v_1;
	v_8 = cursor$0;
	lab13 = true;
lab13:
	while (lab13 === true) {
		lab13 = false;
	golab14:
		while (true) {
			lab15 = true;
		lab15:
			while (lab15 === true) {
				lab15 = false;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, PortugueseStemmer.g_v, 97, 250)) {
					break lab15;
				}
				break golab14;
			}
			if ($this.cursor >= $this.limit) {
				break lab13;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
	golab16:
		while (true) {
			lab17 = true;
		lab17:
			while (lab17 === true) {
				lab17 = false;
				if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, PortugueseStemmer.g_v, 97, 250)) {
					break lab17;
				}
				break golab16;
			}
			if ($this.cursor >= $this.limit) {
				break lab13;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
		$this.I_p1 = $this.cursor;
	golab18:
		while (true) {
			lab19 = true;
		lab19:
			while (lab19 === true) {
				lab19 = false;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, PortugueseStemmer.g_v, 97, 250)) {
					break lab19;
				}
				break golab18;
			}
			if ($this.cursor >= $this.limit) {
				break lab13;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
	golab20:
		while (true) {
			lab21 = true;
		lab21:
			while (lab21 === true) {
				lab21 = false;
				if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, PortugueseStemmer.g_v, 97, 250)) {
					break lab21;
				}
				break golab20;
			}
			if ($this.cursor >= $this.limit) {
				break lab13;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
		$this.I_p2 = $this.cursor;
	}
	$this.cursor = v_8;
	return true;
};

PortugueseStemmer.r_mark_regions$LPortugueseStemmer$ = PortugueseStemmer$r_mark_regions$LPortugueseStemmer$;

PortugueseStemmer.prototype.r_postlude$ = function () {
	var among_var;
	var v_1;
	var lab1;
	var $__jsx_postinc_t;
replab0:
	while (true) {
		v_1 = this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			this.bra = this.cursor;
			among_var = BaseStemmer$find_among$LBaseStemmer$ALAmong$I(this, PortugueseStemmer.a_1, 3);
			if (among_var === 0) {
				break lab1;
			}
			this.ket = this.cursor;
			switch (among_var) {
			case 0:
				break lab1;
			case 1:
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "\u00E3")) {
					return false;
				}
				break;
			case 2:
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "\u00F5")) {
					return false;
				}
				break;
			case 3:
				if (this.cursor >= this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
				break;
			}
			continue replab0;
		}
		this.cursor = v_1;
		break replab0;
	}
	return true;
};

PortugueseStemmer.prototype.r_postlude = PortugueseStemmer.prototype.r_postlude$;

function PortugueseStemmer$r_postlude$LPortugueseStemmer$($this) {
	var among_var;
	var v_1;
	var lab1;
	var $__jsx_postinc_t;
replab0:
	while (true) {
		v_1 = $this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			$this.bra = $this.cursor;
			among_var = BaseStemmer$find_among$LBaseStemmer$ALAmong$I($this, PortugueseStemmer.a_1, 3);
			if (among_var === 0) {
				break lab1;
			}
			$this.ket = $this.cursor;
			switch (among_var) {
			case 0:
				break lab1;
			case 1:
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "\u00E3")) {
					return false;
				}
				break;
			case 2:
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "\u00F5")) {
					return false;
				}
				break;
			case 3:
				if ($this.cursor >= $this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
				break;
			}
			continue replab0;
		}
		$this.cursor = v_1;
		break replab0;
	}
	return true;
};

PortugueseStemmer.r_postlude$LPortugueseStemmer$ = PortugueseStemmer$r_postlude$LPortugueseStemmer$;

PortugueseStemmer.prototype.r_RV$ = function () {
	return (! (this.I_pV <= this.cursor) ? false : true);
};

PortugueseStemmer.prototype.r_RV = PortugueseStemmer.prototype.r_RV$;

function PortugueseStemmer$r_RV$LPortugueseStemmer$($this) {
	return (! ($this.I_pV <= $this.cursor) ? false : true);
};

PortugueseStemmer.r_RV$LPortugueseStemmer$ = PortugueseStemmer$r_RV$LPortugueseStemmer$;

PortugueseStemmer.prototype.r_R1$ = function () {
	return (! (this.I_p1 <= this.cursor) ? false : true);
};

PortugueseStemmer.prototype.r_R1 = PortugueseStemmer.prototype.r_R1$;

function PortugueseStemmer$r_R1$LPortugueseStemmer$($this) {
	return (! ($this.I_p1 <= $this.cursor) ? false : true);
};

PortugueseStemmer.r_R1$LPortugueseStemmer$ = PortugueseStemmer$r_R1$LPortugueseStemmer$;

PortugueseStemmer.prototype.r_R2$ = function () {
	return (! (this.I_p2 <= this.cursor) ? false : true);
};

PortugueseStemmer.prototype.r_R2 = PortugueseStemmer.prototype.r_R2$;

function PortugueseStemmer$r_R2$LPortugueseStemmer$($this) {
	return (! ($this.I_p2 <= $this.cursor) ? false : true);
};

PortugueseStemmer.r_R2$LPortugueseStemmer$ = PortugueseStemmer$r_R2$LPortugueseStemmer$;

PortugueseStemmer.prototype.r_standard_suffix$ = function () {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, PortugueseStemmer.a_5, 45);
	if (among_var === 0) {
		return false;
	}
	this.bra = this.cursor;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 2:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "log")) {
			return false;
		}
		break;
	case 3:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "u")) {
			return false;
		}
		break;
	case 4:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ente")) {
			return false;
		}
		break;
	case 5:
		if (! (! (this.I_p1 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		v_1 = ((this.limit - this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			this.ket = this.cursor;
			among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, PortugueseStemmer.a_2, 4);
			if (among_var === 0) {
				this.cursor = ((this.limit - v_1) | 0);
				break lab0;
			}
			this.bra = cursor$0 = this.cursor;
			if (! (! (this.I_p2 <= cursor$0) ? false : true)) {
				this.cursor = ((this.limit - v_1) | 0);
				break lab0;
			}
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
			switch (among_var) {
			case 0:
				this.cursor = ((this.limit - v_1) | 0);
				break lab0;
			case 1:
				this.ket = this.cursor;
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 2, "at")) {
					this.cursor = ((this.limit - v_1) | 0);
					break lab0;
				}
				this.bra = cursor$1 = this.cursor;
				if (! (! (this.I_p2 <= cursor$1) ? false : true)) {
					this.cursor = ((this.limit - v_1) | 0);
					break lab0;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
					return false;
				}
				break;
			}
		}
		break;
	case 6:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		v_2 = ((this.limit - this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			this.ket = this.cursor;
			among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, PortugueseStemmer.a_3, 3);
			if (among_var === 0) {
				this.cursor = ((this.limit - v_2) | 0);
				break lab1;
			}
			this.bra = this.cursor;
			switch (among_var) {
			case 0:
				this.cursor = ((this.limit - v_2) | 0);
				break lab1;
			case 1:
				if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
					this.cursor = ((this.limit - v_2) | 0);
					break lab1;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
					return false;
				}
				break;
			}
		}
		break;
	case 7:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		v_3 = ((this.limit - this.cursor) | 0);
		lab2 = true;
	lab2:
		while (lab2 === true) {
			lab2 = false;
			this.ket = this.cursor;
			among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, PortugueseStemmer.a_4, 3);
			if (among_var === 0) {
				this.cursor = ((this.limit - v_3) | 0);
				break lab2;
			}
			this.bra = this.cursor;
			switch (among_var) {
			case 0:
				this.cursor = ((this.limit - v_3) | 0);
				break lab2;
			case 1:
				if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
					this.cursor = ((this.limit - v_3) | 0);
					break lab2;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
					return false;
				}
				break;
			}
		}
		break;
	case 8:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		v_4 = ((this.limit - this.cursor) | 0);
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			this.ket = this.cursor;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 2, "at")) {
				this.cursor = ((this.limit - v_4) | 0);
				break lab3;
			}
			this.bra = cursor$2 = this.cursor;
			if (! (! (this.I_p2 <= cursor$2) ? false : true)) {
				this.cursor = ((this.limit - v_4) | 0);
				break lab3;
			}
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
		}
		break;
	case 9:
		if (! (! (this.I_pV <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "e")) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ir")) {
			return false;
		}
		break;
	}
	return true;
};

PortugueseStemmer.prototype.r_standard_suffix = PortugueseStemmer.prototype.r_standard_suffix$;

function PortugueseStemmer$r_standard_suffix$LPortugueseStemmer$($this) {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, PortugueseStemmer.a_5, 45);
	if (among_var === 0) {
		return false;
	}
	$this.bra = $this.cursor;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 2:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "log")) {
			return false;
		}
		break;
	case 3:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "u")) {
			return false;
		}
		break;
	case 4:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ente")) {
			return false;
		}
		break;
	case 5:
		if (! (! ($this.I_p1 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		v_1 = (($this.limit - $this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			$this.ket = $this.cursor;
			among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, PortugueseStemmer.a_2, 4);
			if (among_var === 0) {
				$this.cursor = (($this.limit - v_1) | 0);
				break lab0;
			}
			$this.bra = cursor$0 = $this.cursor;
			if (! (! ($this.I_p2 <= cursor$0) ? false : true)) {
				$this.cursor = (($this.limit - v_1) | 0);
				break lab0;
			}
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
			switch (among_var) {
			case 0:
				$this.cursor = (($this.limit - v_1) | 0);
				break lab0;
			case 1:
				$this.ket = $this.cursor;
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 2, "at")) {
					$this.cursor = (($this.limit - v_1) | 0);
					break lab0;
				}
				$this.bra = cursor$1 = $this.cursor;
				if (! (! ($this.I_p2 <= cursor$1) ? false : true)) {
					$this.cursor = (($this.limit - v_1) | 0);
					break lab0;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
					return false;
				}
				break;
			}
		}
		break;
	case 6:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		v_2 = (($this.limit - $this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			$this.ket = $this.cursor;
			among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, PortugueseStemmer.a_3, 3);
			if (among_var === 0) {
				$this.cursor = (($this.limit - v_2) | 0);
				break lab1;
			}
			$this.bra = $this.cursor;
			switch (among_var) {
			case 0:
				$this.cursor = (($this.limit - v_2) | 0);
				break lab1;
			case 1:
				if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
					$this.cursor = (($this.limit - v_2) | 0);
					break lab1;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
					return false;
				}
				break;
			}
		}
		break;
	case 7:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		v_3 = (($this.limit - $this.cursor) | 0);
		lab2 = true;
	lab2:
		while (lab2 === true) {
			lab2 = false;
			$this.ket = $this.cursor;
			among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, PortugueseStemmer.a_4, 3);
			if (among_var === 0) {
				$this.cursor = (($this.limit - v_3) | 0);
				break lab2;
			}
			$this.bra = $this.cursor;
			switch (among_var) {
			case 0:
				$this.cursor = (($this.limit - v_3) | 0);
				break lab2;
			case 1:
				if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
					$this.cursor = (($this.limit - v_3) | 0);
					break lab2;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
					return false;
				}
				break;
			}
		}
		break;
	case 8:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		v_4 = (($this.limit - $this.cursor) | 0);
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			$this.ket = $this.cursor;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 2, "at")) {
				$this.cursor = (($this.limit - v_4) | 0);
				break lab3;
			}
			$this.bra = cursor$2 = $this.cursor;
			if (! (! ($this.I_p2 <= cursor$2) ? false : true)) {
				$this.cursor = (($this.limit - v_4) | 0);
				break lab3;
			}
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
		}
		break;
	case 9:
		if (! (! ($this.I_pV <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "e")) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ir")) {
			return false;
		}
		break;
	}
	return true;
};

PortugueseStemmer.r_standard_suffix$LPortugueseStemmer$ = PortugueseStemmer$r_standard_suffix$LPortugueseStemmer$;

PortugueseStemmer.prototype.r_verb_suffix$ = function () {
	var among_var;
	var v_1;
	var v_2;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	v_1 = ((this.limit - (cursor$0 = this.cursor)) | 0);
	if (cursor$0 < this.I_pV) {
		return false;
	}
	cursor$1 = this.cursor = this.I_pV;
	v_2 = this.limit_backward;
	this.limit_backward = cursor$1;
	cursor$2 = this.cursor = ((this.limit - v_1) | 0);
	this.ket = cursor$2;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, PortugueseStemmer.a_6, 120);
	if (among_var === 0) {
		this.limit_backward = v_2;
		return false;
	}
	this.bra = this.cursor;
	switch (among_var) {
	case 0:
		this.limit_backward = v_2;
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	}
	this.limit_backward = v_2;
	return true;
};

PortugueseStemmer.prototype.r_verb_suffix = PortugueseStemmer.prototype.r_verb_suffix$;

function PortugueseStemmer$r_verb_suffix$LPortugueseStemmer$($this) {
	var among_var;
	var v_1;
	var v_2;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	v_1 = (($this.limit - (cursor$0 = $this.cursor)) | 0);
	if (cursor$0 < $this.I_pV) {
		return false;
	}
	cursor$1 = $this.cursor = $this.I_pV;
	v_2 = $this.limit_backward;
	$this.limit_backward = cursor$1;
	cursor$2 = $this.cursor = (($this.limit - v_1) | 0);
	$this.ket = cursor$2;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, PortugueseStemmer.a_6, 120);
	if (among_var === 0) {
		$this.limit_backward = v_2;
		return false;
	}
	$this.bra = $this.cursor;
	switch (among_var) {
	case 0:
		$this.limit_backward = v_2;
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	}
	$this.limit_backward = v_2;
	return true;
};

PortugueseStemmer.r_verb_suffix$LPortugueseStemmer$ = PortugueseStemmer$r_verb_suffix$LPortugueseStemmer$;

PortugueseStemmer.prototype.r_residual_suffix$ = function () {
	var among_var;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, PortugueseStemmer.a_7, 7);
	if (among_var === 0) {
		return false;
	}
	this.bra = this.cursor;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! (! (this.I_pV <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	}
	return true;
};

PortugueseStemmer.prototype.r_residual_suffix = PortugueseStemmer.prototype.r_residual_suffix$;

function PortugueseStemmer$r_residual_suffix$LPortugueseStemmer$($this) {
	var among_var;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, PortugueseStemmer.a_7, 7);
	if (among_var === 0) {
		return false;
	}
	$this.bra = $this.cursor;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! (! ($this.I_pV <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	}
	return true;
};

PortugueseStemmer.r_residual_suffix$LPortugueseStemmer$ = PortugueseStemmer$r_residual_suffix$LPortugueseStemmer$;

PortugueseStemmer.prototype.r_residual_form$ = function () {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var lab0;
	var lab1;
	var cursor$0;
	var cursor$1;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, PortugueseStemmer.a_8, 4);
	if (among_var === 0) {
		return false;
	}
	this.bra = this.cursor;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! (! (this.I_pV <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		this.ket = this.cursor;
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			v_1 = ((this.limit - this.cursor) | 0);
			lab1 = true;
		lab1:
			while (lab1 === true) {
				lab1 = false;
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "u")) {
					break lab1;
				}
				this.bra = cursor$0 = this.cursor;
				v_2 = ((this.limit - cursor$0) | 0);
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "g")) {
					break lab1;
				}
				this.cursor = ((this.limit - v_2) | 0);
				break lab0;
			}
			this.cursor = ((this.limit - v_1) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "i")) {
				return false;
			}
			this.bra = cursor$1 = this.cursor;
			v_3 = ((this.limit - cursor$1) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "c")) {
				return false;
			}
			this.cursor = ((this.limit - v_3) | 0);
		}
		if (! (! (this.I_pV <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "c")) {
			return false;
		}
		break;
	}
	return true;
};

PortugueseStemmer.prototype.r_residual_form = PortugueseStemmer.prototype.r_residual_form$;

function PortugueseStemmer$r_residual_form$LPortugueseStemmer$($this) {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var lab0;
	var lab1;
	var cursor$0;
	var cursor$1;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, PortugueseStemmer.a_8, 4);
	if (among_var === 0) {
		return false;
	}
	$this.bra = $this.cursor;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! (! ($this.I_pV <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		$this.ket = $this.cursor;
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			v_1 = (($this.limit - $this.cursor) | 0);
			lab1 = true;
		lab1:
			while (lab1 === true) {
				lab1 = false;
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "u")) {
					break lab1;
				}
				$this.bra = cursor$0 = $this.cursor;
				v_2 = (($this.limit - cursor$0) | 0);
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "g")) {
					break lab1;
				}
				$this.cursor = (($this.limit - v_2) | 0);
				break lab0;
			}
			$this.cursor = (($this.limit - v_1) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "i")) {
				return false;
			}
			$this.bra = cursor$1 = $this.cursor;
			v_3 = (($this.limit - cursor$1) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "c")) {
				return false;
			}
			$this.cursor = (($this.limit - v_3) | 0);
		}
		if (! (! ($this.I_pV <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "c")) {
			return false;
		}
		break;
	}
	return true;
};

PortugueseStemmer.r_residual_form$LPortugueseStemmer$ = PortugueseStemmer$r_residual_form$LPortugueseStemmer$;

PortugueseStemmer.prototype.stem$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_10;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var lab4;
	var lab5;
	var lab6;
	var lab7;
	var lab8;
	var lab9;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var limit$0;
	var cursor$3;
	var cursor$4;
	var limit$1;
	var cursor$5;
	var cursor$6;
	v_1 = this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		if (! PortugueseStemmer$r_prelude$LPortugueseStemmer$(this)) {
			break lab0;
		}
	}
	cursor$0 = this.cursor = v_1;
	v_2 = cursor$0;
	lab1 = true;
lab1:
	while (lab1 === true) {
		lab1 = false;
		if (! PortugueseStemmer$r_mark_regions$LPortugueseStemmer$(this)) {
			break lab1;
		}
	}
	cursor$4 = this.cursor = v_2;
	this.limit_backward = cursor$4;
	cursor$5 = this.cursor = limit$1 = this.limit;
	v_3 = ((limit$1 - cursor$5) | 0);
	lab2 = true;
lab2:
	while (lab2 === true) {
		lab2 = false;
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			v_4 = ((this.limit - this.cursor) | 0);
			lab4 = true;
		lab4:
			while (lab4 === true) {
				lab4 = false;
				v_5 = ((this.limit - this.cursor) | 0);
				lab5 = true;
			lab5:
				while (lab5 === true) {
					lab5 = false;
					v_6 = ((this.limit - this.cursor) | 0);
					lab6 = true;
				lab6:
					while (lab6 === true) {
						lab6 = false;
						if (! PortugueseStemmer$r_standard_suffix$LPortugueseStemmer$(this)) {
							break lab6;
						}
						break lab5;
					}
					this.cursor = ((this.limit - v_6) | 0);
					if (! PortugueseStemmer$r_verb_suffix$LPortugueseStemmer$(this)) {
						break lab4;
					}
				}
				cursor$3 = this.cursor = (((limit$0 = this.limit) - v_5) | 0);
				v_7 = ((limit$0 - cursor$3) | 0);
				lab7 = true;
			lab7:
				while (lab7 === true) {
					lab7 = false;
					this.ket = this.cursor;
					if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "i")) {
						break lab7;
					}
					this.bra = cursor$1 = this.cursor;
					v_8 = ((this.limit - cursor$1) | 0);
					if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "c")) {
						break lab7;
					}
					cursor$2 = this.cursor = ((this.limit - v_8) | 0);
					if (! (! (this.I_pV <= cursor$2) ? false : true)) {
						break lab7;
					}
					if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
						return false;
					}
				}
				this.cursor = ((this.limit - v_7) | 0);
				break lab3;
			}
			this.cursor = ((this.limit - v_4) | 0);
			if (! PortugueseStemmer$r_residual_suffix$LPortugueseStemmer$(this)) {
				break lab2;
			}
		}
	}
	this.cursor = ((this.limit - v_3) | 0);
	lab8 = true;
lab8:
	while (lab8 === true) {
		lab8 = false;
		if (! PortugueseStemmer$r_residual_form$LPortugueseStemmer$(this)) {
			break lab8;
		}
	}
	cursor$6 = this.cursor = this.limit_backward;
	v_10 = cursor$6;
	lab9 = true;
lab9:
	while (lab9 === true) {
		lab9 = false;
		if (! PortugueseStemmer$r_postlude$LPortugueseStemmer$(this)) {
			break lab9;
		}
	}
	this.cursor = v_10;
	return true;
};

PortugueseStemmer.prototype.stem = PortugueseStemmer.prototype.stem$;

PortugueseStemmer.prototype.equals$X = function (o) {
	return o instanceof PortugueseStemmer;
};

PortugueseStemmer.prototype.equals = PortugueseStemmer.prototype.equals$X;

function PortugueseStemmer$equals$LPortugueseStemmer$X($this, o) {
	return o instanceof PortugueseStemmer;
};

PortugueseStemmer.equals$LPortugueseStemmer$X = PortugueseStemmer$equals$LPortugueseStemmer$X;

PortugueseStemmer.prototype.hashCode$ = function () {
	var classname;
	var hash;
	var i;
	var char;
	classname = "PortugueseStemmer";
	hash = 0;
	for (i = 0; i < classname.length; i++) {
		char = classname.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash;
	}
	return (hash | 0);
};

PortugueseStemmer.prototype.hashCode = PortugueseStemmer.prototype.hashCode$;

function PortugueseStemmer$hashCode$LPortugueseStemmer$($this) {
	var classname;
	var hash;
	var i;
	var char;
	classname = "PortugueseStemmer";
	hash = 0;
	for (i = 0; i < classname.length; i++) {
		char = classname.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash;
	}
	return (hash | 0);
};

PortugueseStemmer.hashCode$LPortugueseStemmer$ = PortugueseStemmer$hashCode$LPortugueseStemmer$;

PortugueseStemmer.serialVersionUID = 1;
$__jsx_lazy_init(PortugueseStemmer, "methodObject", function () {
	return new PortugueseStemmer();
});
$__jsx_lazy_init(PortugueseStemmer, "a_0", function () {
	return [ new Among("", -1, 3), new Among("\u00E3", 0, 1), new Among("\u00F5", 0, 2) ];
});
$__jsx_lazy_init(PortugueseStemmer, "a_1", function () {
	return [ new Among("", -1, 3), new Among("a~", 0, 1), new Among("o~", 0, 2) ];
});
$__jsx_lazy_init(PortugueseStemmer, "a_2", function () {
	return [ new Among("ic", -1, -1), new Among("ad", -1, -1), new Among("os", -1, -1), new Among("iv", -1, 1) ];
});
$__jsx_lazy_init(PortugueseStemmer, "a_3", function () {
	return [ new Among("ante", -1, 1), new Among("avel", -1, 1), new Among("\u00EDvel", -1, 1) ];
});
$__jsx_lazy_init(PortugueseStemmer, "a_4", function () {
	return [ new Among("ic", -1, 1), new Among("abil", -1, 1), new Among("iv", -1, 1) ];
});
$__jsx_lazy_init(PortugueseStemmer, "a_5", function () {
	return [ new Among("ica", -1, 1), new Among("\u00E2ncia", -1, 1), new Among("\u00EAncia", -1, 4), new Among("ira", -1, 9), new Among("adora", -1, 1), new Among("osa", -1, 1), new Among("ista", -1, 1), new Among("iva", -1, 8), new Among("eza", -1, 1), new Among("log\u00EDa", -1, 2), new Among("idade", -1, 7), new Among("ante", -1, 1), new Among("mente", -1, 6), new Among("amente", 12, 5), new Among("\u00E1vel", -1, 1), new Among("\u00EDvel", -1, 1), new Among("uci\u00F3n", -1, 3), new Among("ico", -1, 1), new Among("ismo", -1, 1), new Among("oso", -1, 1), new Among("amento", -1, 1), new Among("imento", -1, 1), new Among("ivo", -1, 8), new Among("a\u00E7a~o", -1, 1), new Among("ador", -1, 1), new Among("icas", -1, 1), new Among("\u00EAncias", -1, 4), new Among("iras", -1, 9), new Among("adoras", -1, 1), new Among("osas", -1, 1), new Among("istas", -1, 1), new Among("ivas", -1, 8), new Among("ezas", -1, 1), new Among("log\u00EDas", -1, 2), new Among("idades", -1, 7), new Among("uciones", -1, 3), new Among("adores", -1, 1), new Among("antes", -1, 1), new Among("a\u00E7o~es", -1, 1), new Among("icos", -1, 1), new Among("ismos", -1, 1), new Among("osos", -1, 1), new Among("amentos", -1, 1), new Among("imentos", -1, 1), new Among("ivos", -1, 8) ];
});
$__jsx_lazy_init(PortugueseStemmer, "a_6", function () {
	return [ new Among("ada", -1, 1), new Among("ida", -1, 1), new Among("ia", -1, 1), new Among("aria", 2, 1), new Among("eria", 2, 1), new Among("iria", 2, 1), new Among("ara", -1, 1), new Among("era", -1, 1), new Among("ira", -1, 1), new Among("ava", -1, 1), new Among("asse", -1, 1), new Among("esse", -1, 1), new Among("isse", -1, 1), new Among("aste", -1, 1), new Among("este", -1, 1), new Among("iste", -1, 1), new Among("ei", -1, 1), new Among("arei", 16, 1), new Among("erei", 16, 1), new Among("irei", 16, 1), new Among("am", -1, 1), new Among("iam", 20, 1), new Among("ariam", 21, 1), new Among("eriam", 21, 1), new Among("iriam", 21, 1), new Among("aram", 20, 1), new Among("eram", 20, 1), new Among("iram", 20, 1), new Among("avam", 20, 1), new Among("em", -1, 1), new Among("arem", 29, 1), new Among("erem", 29, 1), new Among("irem", 29, 1), new Among("assem", 29, 1), new Among("essem", 29, 1), new Among("issem", 29, 1), new Among("ado", -1, 1), new Among("ido", -1, 1), new Among("ando", -1, 1), new Among("endo", -1, 1), new Among("indo", -1, 1), new Among("ara~o", -1, 1), new Among("era~o", -1, 1), new Among("ira~o", -1, 1), new Among("ar", -1, 1), new Among("er", -1, 1), new Among("ir", -1, 1), new Among("as", -1, 1), new Among("adas", 47, 1), new Among("idas", 47, 1), new Among("ias", 47, 1), new Among("arias", 50, 1), new Among("erias", 50, 1), new Among("irias", 50, 1), new Among("aras", 47, 1), new Among("eras", 47, 1), new Among("iras", 47, 1), new Among("avas", 47, 1), new Among("es", -1, 1), new Among("ardes", 58, 1), new Among("erdes", 58, 1), new Among("irdes", 58, 1), new Among("ares", 58, 1), new Among("eres", 58, 1), new Among("ires", 58, 1), new Among("asses", 58, 1), new Among("esses", 58, 1), new Among("isses", 58, 1), new Among("astes", 58, 1), new Among("estes", 58, 1), new Among("istes", 58, 1), new Among("is", -1, 1), new Among("ais", 71, 1), new Among("eis", 71, 1), new Among("areis", 73, 1), new Among("ereis", 73, 1), new Among("ireis", 73, 1), new Among("\u00E1reis", 73, 1), new Among("\u00E9reis", 73, 1), new Among("\u00EDreis", 73, 1), new Among("\u00E1sseis", 73, 1), new Among("\u00E9sseis", 73, 1), new Among("\u00EDsseis", 73, 1), new Among("\u00E1veis", 73, 1), new Among("\u00EDeis", 73, 1), new Among("ar\u00EDeis", 84, 1), new Among("er\u00EDeis", 84, 1), new Among("ir\u00EDeis", 84, 1), new Among("ados", -1, 1), new Among("idos", -1, 1), new Among("amos", -1, 1), new Among("\u00E1ramos", 90, 1), new Among("\u00E9ramos", 90, 1), new Among("\u00EDramos", 90, 1), new Among("\u00E1vamos", 90, 1), new Among("\u00EDamos", 90, 1), new Among("ar\u00EDamos", 95, 1), new Among("er\u00EDamos", 95, 1), new Among("ir\u00EDamos", 95, 1), new Among("emos", -1, 1), new Among("aremos", 99, 1), new Among("eremos", 99, 1), new Among("iremos", 99, 1), new Among("\u00E1ssemos", 99, 1), new Among("\u00EAssemos", 99, 1), new Among("\u00EDssemos", 99, 1), new Among("imos", -1, 1), new Among("armos", -1, 1), new Among("ermos", -1, 1), new Among("irmos", -1, 1), new Among("\u00E1mos", -1, 1), new Among("ar\u00E1s", -1, 1), new Among("er\u00E1s", -1, 1), new Among("ir\u00E1s", -1, 1), new Among("eu", -1, 1), new Among("iu", -1, 1), new Among("ou", -1, 1), new Among("ar\u00E1", -1, 1), new Among("er\u00E1", -1, 1), new Among("ir\u00E1", -1, 1) ];
});
$__jsx_lazy_init(PortugueseStemmer, "a_7", function () {
	return [ new Among("a", -1, 1), new Among("i", -1, 1), new Among("o", -1, 1), new Among("os", -1, 1), new Among("\u00E1", -1, 1), new Among("\u00ED", -1, 1), new Among("\u00F3", -1, 1) ];
});
$__jsx_lazy_init(PortugueseStemmer, "a_8", function () {
	return [ new Among("e", -1, 1), new Among("\u00E7", -1, 2), new Among("\u00E9", -1, 1), new Among("\u00EA", -1, 1) ];
});
PortugueseStemmer.g_v = [ 17, 65, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 19, 12, 2 ];

var $__jsx_classMap = {
	"src/among.jsx": {
		Among: Among,
		Among$SII: Among,
		Among$SIIF$LBaseStemmer$B$LBaseStemmer$: Among$0
	},
	"src/stemmer.jsx": {
		Stemmer: Stemmer,
		Stemmer$: Stemmer
	},
	"src/base-stemmer.jsx": {
		BaseStemmer: BaseStemmer,
		BaseStemmer$: BaseStemmer
	},
	"src/portuguese-stemmer.jsx": {
		PortugueseStemmer: PortugueseStemmer,
		PortugueseStemmer$: PortugueseStemmer
	}
};


})(JSX);

var Among = JSX.require("src/among.jsx").Among;
var Among$SII = JSX.require("src/among.jsx").Among$SII;
var Stemmer = JSX.require("src/stemmer.jsx").Stemmer;
var BaseStemmer = JSX.require("src/base-stemmer.jsx").BaseStemmer;
var PortugueseStemmer = JSX.require("src/portuguese-stemmer.jsx").PortugueseStemmer;
