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

function RomanianStemmer() {
	BaseStemmer.call(this);
	this.B_standard_suffix_removed = false;
	this.I_p2 = 0;
	this.I_p1 = 0;
	this.I_pV = 0;
};

$__jsx_extend([RomanianStemmer], BaseStemmer);
RomanianStemmer.prototype.copy_from$LRomanianStemmer$ = function (other) {
	this.B_standard_suffix_removed = other.B_standard_suffix_removed;
	this.I_p2 = other.I_p2;
	this.I_p1 = other.I_p1;
	this.I_pV = other.I_pV;
	BaseStemmer$copy_from$LBaseStemmer$LBaseStemmer$(this, other);
};

RomanianStemmer.prototype.copy_from = RomanianStemmer.prototype.copy_from$LRomanianStemmer$;

RomanianStemmer.prototype.r_prelude$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var lab1;
	var lab3;
	var lab4;
	var lab5;
	var cursor$0;
	var $__jsx_postinc_t;
replab0:
	while (true) {
		v_1 = this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
		golab2:
			while (true) {
				v_2 = this.cursor;
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
						break lab3;
					}
					this.bra = this.cursor;
					lab4 = true;
				lab4:
					while (lab4 === true) {
						lab4 = false;
						v_3 = this.cursor;
						lab5 = true;
					lab5:
						while (lab5 === true) {
							lab5 = false;
							if (! BaseStemmer$eq_s$LBaseStemmer$IS(this, 1, "u")) {
								break lab5;
							}
							this.ket = this.cursor;
							if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
								break lab5;
							}
							if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "U")) {
								return false;
							}
							break lab4;
						}
						this.cursor = v_3;
						if (! BaseStemmer$eq_s$LBaseStemmer$IS(this, 1, "i")) {
							break lab3;
						}
						this.ket = this.cursor;
						if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
							break lab3;
						}
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "I")) {
							return false;
						}
					}
					this.cursor = v_2;
					break golab2;
				}
				cursor$0 = this.cursor = v_2;
				if (cursor$0 >= this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
			continue replab0;
		}
		this.cursor = v_1;
		break replab0;
	}
	return true;
};

RomanianStemmer.prototype.r_prelude = RomanianStemmer.prototype.r_prelude$;

function RomanianStemmer$r_prelude$LRomanianStemmer$($this) {
	var v_1;
	var v_2;
	var v_3;
	var lab1;
	var lab3;
	var lab4;
	var lab5;
	var cursor$0;
	var $__jsx_postinc_t;
replab0:
	while (true) {
		v_1 = $this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
		golab2:
			while (true) {
				v_2 = $this.cursor;
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
						break lab3;
					}
					$this.bra = $this.cursor;
					lab4 = true;
				lab4:
					while (lab4 === true) {
						lab4 = false;
						v_3 = $this.cursor;
						lab5 = true;
					lab5:
						while (lab5 === true) {
							lab5 = false;
							if (! BaseStemmer$eq_s$LBaseStemmer$IS($this, 1, "u")) {
								break lab5;
							}
							$this.ket = $this.cursor;
							if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
								break lab5;
							}
							if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "U")) {
								return false;
							}
							break lab4;
						}
						$this.cursor = v_3;
						if (! BaseStemmer$eq_s$LBaseStemmer$IS($this, 1, "i")) {
							break lab3;
						}
						$this.ket = $this.cursor;
						if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
							break lab3;
						}
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "I")) {
							return false;
						}
					}
					$this.cursor = v_2;
					break golab2;
				}
				cursor$0 = $this.cursor = v_2;
				if (cursor$0 >= $this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
			continue replab0;
		}
		$this.cursor = v_1;
		break replab0;
	}
	return true;
};

RomanianStemmer.r_prelude$LRomanianStemmer$ = RomanianStemmer$r_prelude$LRomanianStemmer$;

RomanianStemmer.prototype.r_mark_regions$ = function () {
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
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
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
						if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
							break lab4;
						}
					golab5:
						while (true) {
							lab6 = true;
						lab6:
							while (lab6 === true) {
								lab6 = false;
								if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
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
					if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
						break lab2;
					}
				golab7:
					while (true) {
						lab8 = true;
					lab8:
						while (lab8 === true) {
							lab8 = false;
							if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
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
			if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
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
					if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
						break lab10;
					}
				golab11:
					while (true) {
						lab12 = true;
					lab12:
						while (lab12 === true) {
							lab12 = false;
							if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
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
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
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
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
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
				if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
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
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
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
				if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
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

RomanianStemmer.prototype.r_mark_regions = RomanianStemmer.prototype.r_mark_regions$;

function RomanianStemmer$r_mark_regions$LRomanianStemmer$($this) {
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
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
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
						if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
							break lab4;
						}
					golab5:
						while (true) {
							lab6 = true;
						lab6:
							while (lab6 === true) {
								lab6 = false;
								if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
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
					if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
						break lab2;
					}
				golab7:
					while (true) {
						lab8 = true;
					lab8:
						while (lab8 === true) {
							lab8 = false;
							if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
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
			if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
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
					if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
						break lab10;
					}
				golab11:
					while (true) {
						lab12 = true;
					lab12:
						while (lab12 === true) {
							lab12 = false;
							if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
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
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
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
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
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
				if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
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
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
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
				if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
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

RomanianStemmer.r_mark_regions$LRomanianStemmer$ = RomanianStemmer$r_mark_regions$LRomanianStemmer$;

RomanianStemmer.prototype.r_postlude$ = function () {
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
			among_var = BaseStemmer$find_among$LBaseStemmer$ALAmong$I(this, RomanianStemmer.a_0, 3);
			if (among_var === 0) {
				break lab1;
			}
			this.ket = this.cursor;
			switch (among_var) {
			case 0:
				break lab1;
			case 1:
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "i")) {
					return false;
				}
				break;
			case 2:
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "u")) {
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

RomanianStemmer.prototype.r_postlude = RomanianStemmer.prototype.r_postlude$;

function RomanianStemmer$r_postlude$LRomanianStemmer$($this) {
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
			among_var = BaseStemmer$find_among$LBaseStemmer$ALAmong$I($this, RomanianStemmer.a_0, 3);
			if (among_var === 0) {
				break lab1;
			}
			$this.ket = $this.cursor;
			switch (among_var) {
			case 0:
				break lab1;
			case 1:
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "i")) {
					return false;
				}
				break;
			case 2:
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "u")) {
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

RomanianStemmer.r_postlude$LRomanianStemmer$ = RomanianStemmer$r_postlude$LRomanianStemmer$;

RomanianStemmer.prototype.r_RV$ = function () {
	return (! (this.I_pV <= this.cursor) ? false : true);
};

RomanianStemmer.prototype.r_RV = RomanianStemmer.prototype.r_RV$;

function RomanianStemmer$r_RV$LRomanianStemmer$($this) {
	return (! ($this.I_pV <= $this.cursor) ? false : true);
};

RomanianStemmer.r_RV$LRomanianStemmer$ = RomanianStemmer$r_RV$LRomanianStemmer$;

RomanianStemmer.prototype.r_R1$ = function () {
	return (! (this.I_p1 <= this.cursor) ? false : true);
};

RomanianStemmer.prototype.r_R1 = RomanianStemmer.prototype.r_R1$;

function RomanianStemmer$r_R1$LRomanianStemmer$($this) {
	return (! ($this.I_p1 <= $this.cursor) ? false : true);
};

RomanianStemmer.r_R1$LRomanianStemmer$ = RomanianStemmer$r_R1$LRomanianStemmer$;

RomanianStemmer.prototype.r_R2$ = function () {
	return (! (this.I_p2 <= this.cursor) ? false : true);
};

RomanianStemmer.prototype.r_R2 = RomanianStemmer.prototype.r_R2$;

function RomanianStemmer$r_R2$LRomanianStemmer$($this) {
	return (! ($this.I_p2 <= $this.cursor) ? false : true);
};

RomanianStemmer.r_R2$LRomanianStemmer$ = RomanianStemmer$r_R2$LRomanianStemmer$;

RomanianStemmer.prototype.r_step_0$ = function () {
	var among_var;
	var v_1;
	var lab0;
	var cursor$0;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, RomanianStemmer.a_1, 16);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	if (! (! (this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "i")) {
			return false;
		}
		break;
	case 5:
		v_1 = ((this.limit - this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 2, "ab")) {
				break lab0;
			}
			return false;
		}
		this.cursor = ((this.limit - v_1) | 0);
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "i")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "at")) {
			return false;
		}
		break;
	case 7:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "a\u0163i")) {
			return false;
		}
		break;
	}
	return true;
};

RomanianStemmer.prototype.r_step_0 = RomanianStemmer.prototype.r_step_0$;

function RomanianStemmer$r_step_0$LRomanianStemmer$($this) {
	var among_var;
	var v_1;
	var lab0;
	var cursor$0;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, RomanianStemmer.a_1, 16);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	if (! (! ($this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "i")) {
			return false;
		}
		break;
	case 5:
		v_1 = (($this.limit - $this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 2, "ab")) {
				break lab0;
			}
			return false;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "i")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "at")) {
			return false;
		}
		break;
	case 7:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "a\u0163i")) {
			return false;
		}
		break;
	}
	return true;
};

RomanianStemmer.r_step_0$LRomanianStemmer$ = RomanianStemmer$r_step_0$LRomanianStemmer$;

RomanianStemmer.prototype.r_combo_suffix$ = function () {
	var among_var;
	var v_1;
	var cursor$0;
	var cursor$1;
	v_1 = ((this.limit - (cursor$0 = this.cursor)) | 0);
	this.ket = cursor$0;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, RomanianStemmer.a_2, 46);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$1 = this.cursor;
	if (! (! (this.I_p1 <= cursor$1) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "abil")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ibil")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "iv")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ic")) {
			return false;
		}
		break;
	case 5:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "at")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "it")) {
			return false;
		}
		break;
	}
	this.B_standard_suffix_removed = true;
	this.cursor = ((this.limit - v_1) | 0);
	return true;
};

RomanianStemmer.prototype.r_combo_suffix = RomanianStemmer.prototype.r_combo_suffix$;

function RomanianStemmer$r_combo_suffix$LRomanianStemmer$($this) {
	var among_var;
	var v_1;
	var cursor$0;
	var cursor$1;
	v_1 = (($this.limit - (cursor$0 = $this.cursor)) | 0);
	$this.ket = cursor$0;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, RomanianStemmer.a_2, 46);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$1 = $this.cursor;
	if (! (! ($this.I_p1 <= cursor$1) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "abil")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ibil")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "iv")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ic")) {
			return false;
		}
		break;
	case 5:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "at")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "it")) {
			return false;
		}
		break;
	}
	$this.B_standard_suffix_removed = true;
	$this.cursor = (($this.limit - v_1) | 0);
	return true;
};

RomanianStemmer.r_combo_suffix$LRomanianStemmer$ = RomanianStemmer$r_combo_suffix$LRomanianStemmer$;

RomanianStemmer.prototype.r_standard_suffix$ = function () {
	var among_var;
	var v_1;
	var lab1;
	var cursor$0;
	this.B_standard_suffix_removed = false;
replab0:
	while (true) {
		v_1 = ((this.limit - this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! RomanianStemmer$r_combo_suffix$LRomanianStemmer$(this)) {
				break lab1;
			}
			continue replab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		break replab0;
	}
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, RomanianStemmer.a_3, 62);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	if (! (! (this.I_p2 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "\u0163")) {
			return false;
		}
		this.bra = this.cursor;
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "t")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ist")) {
			return false;
		}
		break;
	}
	this.B_standard_suffix_removed = true;
	return true;
};

RomanianStemmer.prototype.r_standard_suffix = RomanianStemmer.prototype.r_standard_suffix$;

function RomanianStemmer$r_standard_suffix$LRomanianStemmer$($this) {
	var among_var;
	var v_1;
	var lab1;
	var cursor$0;
	$this.B_standard_suffix_removed = false;
replab0:
	while (true) {
		v_1 = (($this.limit - $this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! RomanianStemmer$r_combo_suffix$LRomanianStemmer$($this)) {
				break lab1;
			}
			continue replab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		break replab0;
	}
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, RomanianStemmer.a_3, 62);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	if (! (! ($this.I_p2 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "\u0163")) {
			return false;
		}
		$this.bra = $this.cursor;
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "t")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ist")) {
			return false;
		}
		break;
	}
	$this.B_standard_suffix_removed = true;
	return true;
};

RomanianStemmer.r_standard_suffix$LRomanianStemmer$ = RomanianStemmer$r_standard_suffix$LRomanianStemmer$;

RomanianStemmer.prototype.r_verb_suffix$ = function () {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var lab0;
	var lab1;
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
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, RomanianStemmer.a_4, 94);
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
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			v_3 = ((this.limit - this.cursor) | 0);
			lab1 = true;
		lab1:
			while (lab1 === true) {
				lab1 = false;
				if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII(this, RomanianStemmer.g_v, 97, 259)) {
					break lab1;
				}
				break lab0;
			}
			this.cursor = ((this.limit - v_3) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "u")) {
				this.limit_backward = v_2;
				return false;
			}
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	}
	this.limit_backward = v_2;
	return true;
};

RomanianStemmer.prototype.r_verb_suffix = RomanianStemmer.prototype.r_verb_suffix$;

function RomanianStemmer$r_verb_suffix$LRomanianStemmer$($this) {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var lab0;
	var lab1;
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
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, RomanianStemmer.a_4, 94);
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
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			v_3 = (($this.limit - $this.cursor) | 0);
			lab1 = true;
		lab1:
			while (lab1 === true) {
				lab1 = false;
				if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII($this, RomanianStemmer.g_v, 97, 259)) {
					break lab1;
				}
				break lab0;
			}
			$this.cursor = (($this.limit - v_3) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "u")) {
				$this.limit_backward = v_2;
				return false;
			}
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	}
	$this.limit_backward = v_2;
	return true;
};

RomanianStemmer.r_verb_suffix$LRomanianStemmer$ = RomanianStemmer$r_verb_suffix$LRomanianStemmer$;

RomanianStemmer.prototype.r_vowel_suffix$ = function () {
	var among_var;
	var cursor$0;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, RomanianStemmer.a_5, 5);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	if (! (! (this.I_pV <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	}
	return true;
};

RomanianStemmer.prototype.r_vowel_suffix = RomanianStemmer.prototype.r_vowel_suffix$;

function RomanianStemmer$r_vowel_suffix$LRomanianStemmer$($this) {
	var among_var;
	var cursor$0;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, RomanianStemmer.a_5, 5);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	if (! (! ($this.I_pV <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	}
	return true;
};

RomanianStemmer.r_vowel_suffix$LRomanianStemmer$ = RomanianStemmer$r_vowel_suffix$LRomanianStemmer$;

RomanianStemmer.prototype.stem$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_8;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var lab4;
	var lab5;
	var lab6;
	var lab7;
	var lab8;
	var cursor$0;
	var cursor$1;
	var limit$0;
	var cursor$2;
	var limit$1;
	var cursor$3;
	var limit$2;
	var cursor$4;
	var cursor$5;
	v_1 = this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		if (! RomanianStemmer$r_prelude$LRomanianStemmer$(this)) {
			break lab0;
		}
	}
	cursor$0 = this.cursor = v_1;
	v_2 = cursor$0;
	lab1 = true;
lab1:
	while (lab1 === true) {
		lab1 = false;
		if (! RomanianStemmer$r_mark_regions$LRomanianStemmer$(this)) {
			break lab1;
		}
	}
	cursor$1 = this.cursor = v_2;
	this.limit_backward = cursor$1;
	cursor$2 = this.cursor = limit$0 = this.limit;
	v_3 = ((limit$0 - cursor$2) | 0);
	lab2 = true;
lab2:
	while (lab2 === true) {
		lab2 = false;
		if (! RomanianStemmer$r_step_0$LRomanianStemmer$(this)) {
			break lab2;
		}
	}
	cursor$3 = this.cursor = (((limit$1 = this.limit) - v_3) | 0);
	v_4 = ((limit$1 - cursor$3) | 0);
	lab3 = true;
lab3:
	while (lab3 === true) {
		lab3 = false;
		if (! RomanianStemmer$r_standard_suffix$LRomanianStemmer$(this)) {
			break lab3;
		}
	}
	cursor$4 = this.cursor = (((limit$2 = this.limit) - v_4) | 0);
	v_5 = ((limit$2 - cursor$4) | 0);
	lab4 = true;
lab4:
	while (lab4 === true) {
		lab4 = false;
		lab5 = true;
	lab5:
		while (lab5 === true) {
			lab5 = false;
			v_6 = ((this.limit - this.cursor) | 0);
			lab6 = true;
		lab6:
			while (lab6 === true) {
				lab6 = false;
				if (! this.B_standard_suffix_removed) {
					break lab6;
				}
				break lab5;
			}
			this.cursor = ((this.limit - v_6) | 0);
			if (! RomanianStemmer$r_verb_suffix$LRomanianStemmer$(this)) {
				break lab4;
			}
		}
	}
	this.cursor = ((this.limit - v_5) | 0);
	lab7 = true;
lab7:
	while (lab7 === true) {
		lab7 = false;
		if (! RomanianStemmer$r_vowel_suffix$LRomanianStemmer$(this)) {
			break lab7;
		}
	}
	cursor$5 = this.cursor = this.limit_backward;
	v_8 = cursor$5;
	lab8 = true;
lab8:
	while (lab8 === true) {
		lab8 = false;
		if (! RomanianStemmer$r_postlude$LRomanianStemmer$(this)) {
			break lab8;
		}
	}
	this.cursor = v_8;
	return true;
};

RomanianStemmer.prototype.stem = RomanianStemmer.prototype.stem$;

RomanianStemmer.prototype.equals$X = function (o) {
	return o instanceof RomanianStemmer;
};

RomanianStemmer.prototype.equals = RomanianStemmer.prototype.equals$X;

function RomanianStemmer$equals$LRomanianStemmer$X($this, o) {
	return o instanceof RomanianStemmer;
};

RomanianStemmer.equals$LRomanianStemmer$X = RomanianStemmer$equals$LRomanianStemmer$X;

RomanianStemmer.prototype.hashCode$ = function () {
	var classname;
	var hash;
	var i;
	var char;
	classname = "RomanianStemmer";
	hash = 0;
	for (i = 0; i < classname.length; i++) {
		char = classname.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash;
	}
	return (hash | 0);
};

RomanianStemmer.prototype.hashCode = RomanianStemmer.prototype.hashCode$;

function RomanianStemmer$hashCode$LRomanianStemmer$($this) {
	var classname;
	var hash;
	var i;
	var char;
	classname = "RomanianStemmer";
	hash = 0;
	for (i = 0; i < classname.length; i++) {
		char = classname.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash;
	}
	return (hash | 0);
};

RomanianStemmer.hashCode$LRomanianStemmer$ = RomanianStemmer$hashCode$LRomanianStemmer$;

RomanianStemmer.serialVersionUID = 1;
$__jsx_lazy_init(RomanianStemmer, "methodObject", function () {
	return new RomanianStemmer();
});
$__jsx_lazy_init(RomanianStemmer, "a_0", function () {
	return [ new Among("", -1, 3), new Among("I", 0, 1), new Among("U", 0, 2) ];
});
$__jsx_lazy_init(RomanianStemmer, "a_1", function () {
	return [ new Among("ea", -1, 3), new Among("a\u0163ia", -1, 7), new Among("aua", -1, 2), new Among("iua", -1, 4), new Among("a\u0163ie", -1, 7), new Among("ele", -1, 3), new Among("ile", -1, 5), new Among("iile", 6, 4), new Among("iei", -1, 4), new Among("atei", -1, 6), new Among("ii", -1, 4), new Among("ului", -1, 1), new Among("ul", -1, 1), new Among("elor", -1, 3), new Among("ilor", -1, 4), new Among("iilor", 14, 4) ];
});
$__jsx_lazy_init(RomanianStemmer, "a_2", function () {
	return [ new Among("icala", -1, 4), new Among("iciva", -1, 4), new Among("ativa", -1, 5), new Among("itiva", -1, 6), new Among("icale", -1, 4), new Among("a\u0163iune", -1, 5), new Among("i\u0163iune", -1, 6), new Among("atoare", -1, 5), new Among("itoare", -1, 6), new Among("\u0103toare", -1, 5), new Among("icitate", -1, 4), new Among("abilitate", -1, 1), new Among("ibilitate", -1, 2), new Among("ivitate", -1, 3), new Among("icive", -1, 4), new Among("ative", -1, 5), new Among("itive", -1, 6), new Among("icali", -1, 4), new Among("atori", -1, 5), new Among("icatori", 18, 4), new Among("itori", -1, 6), new Among("\u0103tori", -1, 5), new Among("icitati", -1, 4), new Among("abilitati", -1, 1), new Among("ivitati", -1, 3), new Among("icivi", -1, 4), new Among("ativi", -1, 5), new Among("itivi", -1, 6), new Among("icit\u0103i", -1, 4), new Among("abilit\u0103i", -1, 1), new Among("ivit\u0103i", -1, 3), new Among("icit\u0103\u0163i", -1, 4), new Among("abilit\u0103\u0163i", -1, 1), new Among("ivit\u0103\u0163i", -1, 3), new Among("ical", -1, 4), new Among("ator", -1, 5), new Among("icator", 35, 4), new Among("itor", -1, 6), new Among("\u0103tor", -1, 5), new Among("iciv", -1, 4), new Among("ativ", -1, 5), new Among("itiv", -1, 6), new Among("ical\u0103", -1, 4), new Among("iciv\u0103", -1, 4), new Among("ativ\u0103", -1, 5), new Among("itiv\u0103", -1, 6) ];
});
$__jsx_lazy_init(RomanianStemmer, "a_3", function () {
	return [ new Among("ica", -1, 1), new Among("abila", -1, 1), new Among("ibila", -1, 1), new Among("oasa", -1, 1), new Among("ata", -1, 1), new Among("ita", -1, 1), new Among("anta", -1, 1), new Among("ista", -1, 3), new Among("uta", -1, 1), new Among("iva", -1, 1), new Among("ic", -1, 1), new Among("ice", -1, 1), new Among("abile", -1, 1), new Among("ibile", -1, 1), new Among("isme", -1, 3), new Among("iune", -1, 2), new Among("oase", -1, 1), new Among("ate", -1, 1), new Among("itate", 17, 1), new Among("ite", -1, 1), new Among("ante", -1, 1), new Among("iste", -1, 3), new Among("ute", -1, 1), new Among("ive", -1, 1), new Among("ici", -1, 1), new Among("abili", -1, 1), new Among("ibili", -1, 1), new Among("iuni", -1, 2), new Among("atori", -1, 1), new Among("osi", -1, 1), new Among("ati", -1, 1), new Among("itati", 30, 1), new Among("iti", -1, 1), new Among("anti", -1, 1), new Among("isti", -1, 3), new Among("uti", -1, 1), new Among("i\u015Fti", -1, 3), new Among("ivi", -1, 1), new Among("it\u0103i", -1, 1), new Among("o\u015Fi", -1, 1), new Among("it\u0103\u0163i", -1, 1), new Among("abil", -1, 1), new Among("ibil", -1, 1), new Among("ism", -1, 3), new Among("ator", -1, 1), new Among("os", -1, 1), new Among("at", -1, 1), new Among("it", -1, 1), new Among("ant", -1, 1), new Among("ist", -1, 3), new Among("ut", -1, 1), new Among("iv", -1, 1), new Among("ic\u0103", -1, 1), new Among("abil\u0103", -1, 1), new Among("ibil\u0103", -1, 1), new Among("oas\u0103", -1, 1), new Among("at\u0103", -1, 1), new Among("it\u0103", -1, 1), new Among("ant\u0103", -1, 1), new Among("ist\u0103", -1, 3), new Among("ut\u0103", -1, 1), new Among("iv\u0103", -1, 1) ];
});
$__jsx_lazy_init(RomanianStemmer, "a_4", function () {
	return [ new Among("ea", -1, 1), new Among("ia", -1, 1), new Among("esc", -1, 1), new Among("\u0103sc", -1, 1), new Among("ind", -1, 1), new Among("\u00E2nd", -1, 1), new Among("are", -1, 1), new Among("ere", -1, 1), new Among("ire", -1, 1), new Among("\u00E2re", -1, 1), new Among("se", -1, 2), new Among("ase", 10, 1), new Among("sese", 10, 2), new Among("ise", 10, 1), new Among("use", 10, 1), new Among("\u00E2se", 10, 1), new Among("e\u015Fte", -1, 1), new Among("\u0103\u015Fte", -1, 1), new Among("eze", -1, 1), new Among("ai", -1, 1), new Among("eai", 19, 1), new Among("iai", 19, 1), new Among("sei", -1, 2), new Among("e\u015Fti", -1, 1), new Among("\u0103\u015Fti", -1, 1), new Among("ui", -1, 1), new Among("ezi", -1, 1), new Among("\u00E2i", -1, 1), new Among("a\u015Fi", -1, 1), new Among("se\u015Fi", -1, 2), new Among("ase\u015Fi", 29, 1), new Among("sese\u015Fi", 29, 2), new Among("ise\u015Fi", 29, 1), new Among("use\u015Fi", 29, 1), new Among("\u00E2se\u015Fi", 29, 1), new Among("i\u015Fi", -1, 1), new Among("u\u015Fi", -1, 1), new Among("\u00E2\u015Fi", -1, 1), new Among("a\u0163i", -1, 2), new Among("ea\u0163i", 38, 1), new Among("ia\u0163i", 38, 1), new Among("e\u0163i", -1, 2), new Among("i\u0163i", -1, 2), new Among("\u00E2\u0163i", -1, 2), new Among("ar\u0103\u0163i", -1, 1), new Among("ser\u0103\u0163i", -1, 2), new Among("aser\u0103\u0163i", 45, 1), new Among("seser\u0103\u0163i", 45, 2), new Among("iser\u0103\u0163i", 45, 1), new Among("user\u0103\u0163i", 45, 1), new Among("\u00E2ser\u0103\u0163i", 45, 1), new Among("ir\u0103\u0163i", -1, 1), new Among("ur\u0103\u0163i", -1, 1), new Among("\u00E2r\u0103\u0163i", -1, 1), new Among("am", -1, 1), new Among("eam", 54, 1), new Among("iam", 54, 1), new Among("em", -1, 2), new Among("asem", 57, 1), new Among("sesem", 57, 2), new Among("isem", 57, 1), new Among("usem", 57, 1), new Among("\u00E2sem", 57, 1), new Among("im", -1, 2), new Among("\u00E2m", -1, 2), new Among("\u0103m", -1, 2), new Among("ar\u0103m", 65, 1), new Among("ser\u0103m", 65, 2), new Among("aser\u0103m", 67, 1), new Among("seser\u0103m", 67, 2), new Among("iser\u0103m", 67, 1), new Among("user\u0103m", 67, 1), new Among("\u00E2ser\u0103m", 67, 1), new Among("ir\u0103m", 65, 1), new Among("ur\u0103m", 65, 1), new Among("\u00E2r\u0103m", 65, 1), new Among("au", -1, 1), new Among("eau", 76, 1), new Among("iau", 76, 1), new Among("indu", -1, 1), new Among("\u00E2ndu", -1, 1), new Among("ez", -1, 1), new Among("easc\u0103", -1, 1), new Among("ar\u0103", -1, 1), new Among("ser\u0103", -1, 2), new Among("aser\u0103", 84, 1), new Among("seser\u0103", 84, 2), new Among("iser\u0103", 84, 1), new Among("user\u0103", 84, 1), new Among("\u00E2ser\u0103", 84, 1), new Among("ir\u0103", -1, 1), new Among("ur\u0103", -1, 1), new Among("\u00E2r\u0103", -1, 1), new Among("eaz\u0103", -1, 1) ];
});
$__jsx_lazy_init(RomanianStemmer, "a_5", function () {
	return [ new Among("a", -1, 1), new Among("e", -1, 1), new Among("ie", 1, 1), new Among("i", -1, 1), new Among("\u0103", -1, 1) ];
});
RomanianStemmer.g_v = [ 17, 65, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 32, 0, 0, 4 ];

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
	"src/romanian-stemmer.jsx": {
		RomanianStemmer: RomanianStemmer,
		RomanianStemmer$: RomanianStemmer
	}
};


})(JSX);

var Among = JSX.require("src/among.jsx").Among;
var Among$SII = JSX.require("src/among.jsx").Among$SII;
var Stemmer = JSX.require("src/stemmer.jsx").Stemmer;
var BaseStemmer = JSX.require("src/base-stemmer.jsx").BaseStemmer;
var RomanianStemmer = JSX.require("src/romanian-stemmer.jsx").RomanianStemmer;
