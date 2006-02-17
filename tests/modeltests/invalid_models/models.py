"""
26. A test to check that the model validator works can correctly identify errors in a model. 
"""

from django.db import models

class FieldErrors(models.Model):
    charfield = models.CharField()
    floatfield = models.FloatField()
    filefield = models.FileField()
    prepopulate = models.CharField(maxlength=10, prepopulate_from='bad')
    choices = models.CharField(maxlength=10, choices='bad')
    choices2 = models.CharField(maxlength=10, choices=[(1,2,3),(1,2,3)])
    index = models.CharField(maxlength=10, db_index='bad')    

class Target(models.Model):
    tgt_safe = models.CharField(maxlength=10)
    
    clash1_set = models.CharField(maxlength=10)
    
class Clash1(models.Model):
    src_safe = models.CharField(maxlength=10)
    
    foreign = models.ForeignKey(Target)
    m2m = models.ManyToManyField(Target)

class Clash2(models.Model):
    src_safe = models.CharField(maxlength=10)

    foreign_1 = models.ForeignKey(Target, related_name='id')
    foreign_2 = models.ForeignKey(Target, related_name='src_safe')

    m2m_1 = models.ManyToManyField(Target, related_name='id')
    m2m_2 = models.ManyToManyField(Target, related_name='src_safe')

class Target2(models.Model):
    foreign_tgt = models.ForeignKey(Target)
    clashforeign_set = models.ForeignKey(Target)
    
    m2m_tgt = models.ManyToManyField(Target)
    clashm2m_set = models.ManyToManyField(Target)

class Clash3(models.Model):
    foreign_1 = models.ForeignKey(Target2, related_name='foreign_tgt')
    foreign_2 = models.ForeignKey(Target2, related_name='m2m_tgt')
    
    m2m_1 = models.ManyToManyField(Target2, related_name='foreign_tgt')
    m2m_2 = models.ManyToManyField(Target2, related_name='m2m_tgt')
    
class ClashForeign(models.Model):
    foreign = models.ForeignKey(Target2)

class ClashM2M(models.Model):
    m2m = models.ManyToManyField(Target2)
    
class SelfClashForeign(models.Model):
    src_safe = models.CharField(maxlength=10)
    
    selfclashforeign_set = models.ForeignKey("SelfClashForeign") 
    foreign_1 = models.ForeignKey("SelfClashForeign", related_name='id')
    foreign_2 = models.ForeignKey("SelfClashForeign", related_name='src_safe')

class SelfClashM2M(models.Model):
    src_safe = models.CharField(maxlength=10)

    selfclashm2m_set = models.ManyToManyField("SelfClashM2M")
    m2m_1 = models.ManyToManyField("SelfClashM2M", related_name='id')
    m2m_2 = models.ManyToManyField("SelfClashM2M", related_name='src_safe')

error_log = """invalid_models.fielderrors: "charfield": CharFields require a "maxlength" attribute.
invalid_models.fielderrors: "floatfield": FloatFields require a "decimal_places" attribute.
invalid_models.fielderrors: "floatfield": FloatFields require a "max_digits" attribute.
invalid_models.fielderrors: "filefield": FileFields require an "upload_to" attribute.
invalid_models.fielderrors: "prepopulate": prepopulate_from should be a list or tuple.
invalid_models.fielderrors: "choices": "choices" should be either a tuple or list.
invalid_models.fielderrors: "choices2": "choices" should be a sequence of two-tuples.
invalid_models.fielderrors: "choices2": "choices" should be a sequence of two-tuples.
invalid_models.fielderrors: "index": "db_index" should be either None, True or False.
invalid_models.clash1: 'foreign' accessor name 'Target.clash1_set' clashes with another field
invalid_models.clash1: 'foreign' accessor name 'Target.clash1_set' clashes with a related m2m field
invalid_models.clash1: 'm2m' m2m accessor name 'Target.clash1_set' clashes with another field
invalid_models.clash1: 'm2m' m2m accessor name 'Target.clash1_set' clashes with a related field
invalid_models.clash2: 'foreign_1' accessor name 'Target.id' clashes with another field
invalid_models.clash2: 'foreign_1' accessor name 'Target.id' clashes with a related m2m field
invalid_models.clash2: 'foreign_2' accessor name 'Target.src_safe' clashes with a related m2m field
invalid_models.clash2: 'm2m_1' m2m accessor name 'Target.id' clashes with another field
invalid_models.clash2: 'm2m_1' m2m accessor name 'Target.id' clashes with a related field
invalid_models.clash2: 'm2m_2' m2m accessor name 'Target.src_safe' clashes with a related field
invalid_models.clash3: 'foreign_1' accessor name 'Target2.foreign_tgt' clashes with another field
invalid_models.clash3: 'foreign_1' accessor name 'Target2.foreign_tgt' clashes with a related m2m field
invalid_models.clash3: 'foreign_2' accessor name 'Target2.m2m_tgt' clashes with a m2m field
invalid_models.clash3: 'foreign_2' accessor name 'Target2.m2m_tgt' clashes with a related m2m field
invalid_models.clash3: 'm2m_1' m2m accessor name 'Target2.foreign_tgt' clashes with another field
invalid_models.clash3: 'm2m_1' m2m accessor name 'Target2.foreign_tgt' clashes with a related field
invalid_models.clash3: 'm2m_2' m2m accessor name 'Target2.m2m_tgt' clashes with a m2m field
invalid_models.clash3: 'm2m_2' m2m accessor name 'Target2.m2m_tgt' clashes with a related field
invalid_models.clashforeign: 'foreign' accessor name 'Target2.clashforeign_set' clashes with another field
invalid_models.clashm2m: 'm2m' m2m accessor name 'Target2.clashm2m_set' clashes with a m2m field
invalid_models.target2: 'foreign_tgt' accessor name 'Target.target2_set' clashes with a related m2m field
invalid_models.target2: 'foreign_tgt' accessor name 'Target.target2_set' clashes with a related m2m field
invalid_models.target2: 'foreign_tgt' accessor name 'Target.target2_set' clashes with a related field
invalid_models.target2: 'clashforeign_set' accessor name 'Target.target2_set' clashes with a related m2m field
invalid_models.target2: 'clashforeign_set' accessor name 'Target.target2_set' clashes with a related m2m field
invalid_models.target2: 'clashforeign_set' accessor name 'Target.target2_set' clashes with a related field
invalid_models.target2: 'm2m_tgt' m2m accessor name 'Target.target2_set' clashes with a related m2m field
invalid_models.target2: 'm2m_tgt' m2m accessor name 'Target.target2_set' clashes with a related field
invalid_models.target2: 'm2m_tgt' m2m accessor name 'Target.target2_set' clashes with a related field
invalid_models.target2: 'clashm2m_set' m2m accessor name 'Target.target2_set' clashes with a related m2m field
invalid_models.target2: 'clashm2m_set' m2m accessor name 'Target.target2_set' clashes with a related field
invalid_models.target2: 'clashm2m_set' m2m accessor name 'Target.target2_set' clashes with a related field
invalid_models.selfclashforeign: 'selfclashforeign_set' accessor name 'SelfClashForeign.selfclashforeign_set' clashes with another field
invalid_models.selfclashforeign: 'foreign_1' accessor name 'SelfClashForeign.id' clashes with another field
invalid_models.selfclashforeign: 'foreign_2' accessor name 'SelfClashForeign.src_safe' clashes with another field
invalid_models.selfclashm2m: 'selfclashm2m_set' m2m accessor name 'SelfClashM2M.selfclashm2m_set' clashes with a m2m field
invalid_models.selfclashm2m: 'm2m_1' m2m accessor name 'SelfClashM2M.id' clashes with another field
invalid_models.selfclashm2m: 'm2m_2' m2m accessor name 'SelfClashM2M.src_safe' clashes with another field
"""
