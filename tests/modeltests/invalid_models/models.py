"""
26. Invalid models

This example exists purely to point out errors in models.
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
    clash1 = models.CharField(maxlength=10)
    clash2 = models.CharField(maxlength=10)

    clash1_set = models.CharField(maxlength=10)

class Clash1(models.Model):
    src_safe = models.CharField(maxlength=10, core=True)

    foreign = models.ForeignKey(Target)
    m2m = models.ManyToManyField(Target)

class Clash2(models.Model):
    src_safe = models.CharField(maxlength=10, core=True)

    foreign_1 = models.ForeignKey(Target, related_name='id')
    foreign_2 = models.ForeignKey(Target, related_name='src_safe')

    m2m_1 = models.ManyToManyField(Target, related_name='id')
    m2m_2 = models.ManyToManyField(Target, related_name='src_safe')

class Target2(models.Model):
    clash3 = models.CharField(maxlength=10)
    foreign_tgt = models.ForeignKey(Target)
    clashforeign_set = models.ForeignKey(Target)

    m2m_tgt = models.ManyToManyField(Target)
    clashm2m_set = models.ManyToManyField(Target)

class Clash3(models.Model):
    src_safe = models.CharField(maxlength=10, core=True)
    
    foreign_1 = models.ForeignKey(Target2, related_name='foreign_tgt')
    foreign_2 = models.ForeignKey(Target2, related_name='m2m_tgt')

    m2m_1 = models.ManyToManyField(Target2, related_name='foreign_tgt')
    m2m_2 = models.ManyToManyField(Target2, related_name='m2m_tgt')

class ClashForeign(models.Model):
    foreign = models.ForeignKey(Target2)

class ClashM2M(models.Model):
    m2m = models.ManyToManyField(Target2)

class SelfClashForeign(models.Model):
    src_safe = models.CharField(maxlength=10, core=True)
    selfclashforeign = models.CharField(maxlength=10)

    selfclashforeign_set = models.ForeignKey("SelfClashForeign")
    foreign_1 = models.ForeignKey("SelfClashForeign", related_name='id')
    foreign_2 = models.ForeignKey("SelfClashForeign", related_name='src_safe')

class ValidM2M(models.Model):
    src_safe = models.CharField(maxlength=10)
    validm2m = models.CharField(maxlength=10)

    # M2M fields are symmetrical by default. Symmetrical M2M fields
    # on self don't require a related accessor, so many potential
    # clashes are avoided.
    validm2m_set = models.ManyToManyField("ValidM2M")
    
    m2m_1 = models.ManyToManyField("ValidM2M", related_name='id')
    m2m_2 = models.ManyToManyField("ValidM2M", related_name='src_safe')

    m2m_3 = models.ManyToManyField('self')
    m2m_4 = models.ManyToManyField('self')

class SelfClashM2M(models.Model):
    src_safe = models.CharField(maxlength=10)
    selfclashm2m = models.CharField(maxlength=10)

    # Non-symmetrical M2M fields _do_ have related accessors, so 
    # there is potential for clashes.
    selfclashm2m_set = models.ManyToManyField("SelfClashM2M", symmetrical=False)
    
    m2m_1 = models.ManyToManyField("SelfClashM2M", related_name='id', symmetrical=False)
    m2m_2 = models.ManyToManyField("SelfClashM2M", related_name='src_safe', symmetrical=False)

    m2m_3 = models.ManyToManyField('self', symmetrical=False)
    m2m_4 = models.ManyToManyField('self', symmetrical=False)

model_errors = """invalid_models.fielderrors: "charfield": CharFields require a "maxlength" attribute.
invalid_models.fielderrors: "floatfield": FloatFields require a "decimal_places" attribute.
invalid_models.fielderrors: "floatfield": FloatFields require a "max_digits" attribute.
invalid_models.fielderrors: "filefield": FileFields require an "upload_to" attribute.
invalid_models.fielderrors: "prepopulate": prepopulate_from should be a list or tuple.
invalid_models.fielderrors: "choices": "choices" should be iterable (e.g., a tuple or list).
invalid_models.fielderrors: "choices2": "choices" should be a sequence of two-tuples.
invalid_models.fielderrors: "choices2": "choices" should be a sequence of two-tuples.
invalid_models.fielderrors: "index": "db_index" should be either None, True or False.
invalid_models.clash1: Accessor for field 'foreign' clashes with field 'Target.clash1_set'. Add a related_name argument to the definition for 'foreign'.
invalid_models.clash1: Accessor for field 'foreign' clashes with related m2m field 'Target.clash1_set'. Add a related_name argument to the definition for 'foreign'.
invalid_models.clash1: Reverse query name for field 'foreign' clashes with field 'Target.clash1'. Add a related_name argument to the definition for 'foreign'.
invalid_models.clash1: Accessor for m2m field 'm2m' clashes with field 'Target.clash1_set'. Add a related_name argument to the definition for 'm2m'.
invalid_models.clash1: Accessor for m2m field 'm2m' clashes with related field 'Target.clash1_set'. Add a related_name argument to the definition for 'm2m'.
invalid_models.clash1: Reverse query name for m2m field 'm2m' clashes with field 'Target.clash1'. Add a related_name argument to the definition for 'm2m'.
invalid_models.clash2: Accessor for field 'foreign_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash2: Accessor for field 'foreign_1' clashes with related m2m field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash2: Reverse query name for field 'foreign_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash2: Reverse query name for field 'foreign_1' clashes with related m2m field 'Target.id'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash2: Accessor for field 'foreign_2' clashes with related m2m field 'Target.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.clash2: Reverse query name for field 'foreign_2' clashes with related m2m field 'Target.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.clash2: Accessor for m2m field 'm2m_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash2: Accessor for m2m field 'm2m_1' clashes with related field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash2: Reverse query name for m2m field 'm2m_1' clashes with field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash2: Reverse query name for m2m field 'm2m_1' clashes with related field 'Target.id'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash2: Accessor for m2m field 'm2m_2' clashes with related field 'Target.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.clash2: Reverse query name for m2m field 'm2m_2' clashes with related field 'Target.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.clash3: Accessor for field 'foreign_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash3: Accessor for field 'foreign_1' clashes with related m2m field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash3: Reverse query name for field 'foreign_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash3: Reverse query name for field 'foreign_1' clashes with related m2m field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.clash3: Accessor for field 'foreign_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.clash3: Accessor for field 'foreign_2' clashes with related m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.clash3: Reverse query name for field 'foreign_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.clash3: Reverse query name for field 'foreign_2' clashes with related m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.clash3: Accessor for m2m field 'm2m_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash3: Accessor for m2m field 'm2m_1' clashes with related field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash3: Reverse query name for m2m field 'm2m_1' clashes with field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash3: Reverse query name for m2m field 'm2m_1' clashes with related field 'Target2.foreign_tgt'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.clash3: Accessor for m2m field 'm2m_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.clash3: Accessor for m2m field 'm2m_2' clashes with related field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.clash3: Reverse query name for m2m field 'm2m_2' clashes with m2m field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.clash3: Reverse query name for m2m field 'm2m_2' clashes with related field 'Target2.m2m_tgt'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.clashforeign: Accessor for field 'foreign' clashes with field 'Target2.clashforeign_set'. Add a related_name argument to the definition for 'foreign'.
invalid_models.clashm2m: Accessor for m2m field 'm2m' clashes with m2m field 'Target2.clashm2m_set'. Add a related_name argument to the definition for 'm2m'.
invalid_models.target2: Accessor for field 'foreign_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'foreign_tgt'.
invalid_models.target2: Accessor for field 'foreign_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'foreign_tgt'.
invalid_models.target2: Accessor for field 'foreign_tgt' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'foreign_tgt'.
invalid_models.target2: Accessor for field 'clashforeign_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashforeign_set'.
invalid_models.target2: Accessor for field 'clashforeign_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashforeign_set'.
invalid_models.target2: Accessor for field 'clashforeign_set' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'clashforeign_set'.
invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
invalid_models.target2: Accessor for m2m field 'm2m_tgt' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'm2m_tgt'.
invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
invalid_models.target2: Accessor for m2m field 'clashm2m_set' clashes with related m2m field 'Target.target2_set'. Add a related_name argument to the definition for 'clashm2m_set'.
invalid_models.selfclashforeign: Accessor for field 'selfclashforeign_set' clashes with field 'SelfClashForeign.selfclashforeign_set'. Add a related_name argument to the definition for 'selfclashforeign_set'.
invalid_models.selfclashforeign: Reverse query name for field 'selfclashforeign_set' clashes with field 'SelfClashForeign.selfclashforeign'. Add a related_name argument to the definition for 'selfclashforeign_set'.
invalid_models.selfclashforeign: Accessor for field 'foreign_1' clashes with field 'SelfClashForeign.id'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.selfclashforeign: Reverse query name for field 'foreign_1' clashes with field 'SelfClashForeign.id'. Add a related_name argument to the definition for 'foreign_1'.
invalid_models.selfclashforeign: Accessor for field 'foreign_2' clashes with field 'SelfClashForeign.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.selfclashforeign: Reverse query name for field 'foreign_2' clashes with field 'SelfClashForeign.src_safe'. Add a related_name argument to the definition for 'foreign_2'.
invalid_models.selfclashm2m: Accessor for m2m field 'selfclashm2m_set' clashes with m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'selfclashm2m_set'.
invalid_models.selfclashm2m: Reverse query name for m2m field 'selfclashm2m_set' clashes with field 'SelfClashM2M.selfclashm2m'. Add a related_name argument to the definition for 'selfclashm2m_set'.
invalid_models.selfclashm2m: Accessor for m2m field 'selfclashm2m_set' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'selfclashm2m_set'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_1' clashes with field 'SelfClashM2M.id'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_2' clashes with field 'SelfClashM2M.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_1' clashes with field 'SelfClashM2M.id'. Add a related_name argument to the definition for 'm2m_1'.
invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_2' clashes with field 'SelfClashM2M.src_safe'. Add a related_name argument to the definition for 'm2m_2'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_3' clashes with m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_3'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_3' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_3'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_3' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_3'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_4' clashes with m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_4'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_4' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_4'.
invalid_models.selfclashm2m: Accessor for m2m field 'm2m_4' clashes with related m2m field 'SelfClashM2M.selfclashm2m_set'. Add a related_name argument to the definition for 'm2m_4'.
invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_3' clashes with field 'SelfClashM2M.selfclashm2m'. Add a related_name argument to the definition for 'm2m_3'.
invalid_models.selfclashm2m: Reverse query name for m2m field 'm2m_4' clashes with field 'SelfClashM2M.selfclashm2m'. Add a related_name argument to the definition for 'm2m_4'.
"""
