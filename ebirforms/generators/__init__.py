"""All eBIRForms XML generators.

Each generator takes a TaxpayerInfo and a form-specific data class,
and produces the eBIRForms pseudo-XML file content.
"""

from ebirforms.generators.form_0619e import Form0619EData, Form0619EGenerator
from ebirforms.generators.form_0619f import Form0619FData, Form0619FGenerator
from ebirforms.generators.form_1601eq import Form1601EQData, Form1601EQGenerator
from ebirforms.generators.form_1601fq import Form1601FQData, Form1601FQGenerator
from ebirforms.generators.form_1603q import Form1603QData, Form1603QGenerator
from ebirforms.generators.form_1604e import Form1604EData, Form1604EGenerator
from ebirforms.generators.form_1702ex import Form1702EXData, Form1702EXGenerator
from ebirforms.generators.form_1702mx import Form1702MXData, Form1702MXGenerator
from ebirforms.generators.form_1702q import Form1702QData, Form1702QGenerator
from ebirforms.generators.form_1702rt import Form1702RTData, Form1702RTGenerator
from ebirforms.generators.form_2000 import Form2000Data, Form2000Generator
from ebirforms.generators.form_2550m import Form2550MData, Form2550MGenerator
from ebirforms.generators.form_2550q import Form2550QData, Form2550QGenerator
from ebirforms.generators.form_2551q import Form2551QData, Form2551QGenerator

__all__ = [
    "Form0619EData",
    "Form0619EGenerator",
    "Form0619FData",
    "Form0619FGenerator",
    "Form1601EQData",
    "Form1601EQGenerator",
    "Form1601FQData",
    "Form1601FQGenerator",
    "Form1603QData",
    "Form1603QGenerator",
    "Form1604EData",
    "Form1604EGenerator",
    "Form1702EXData",
    "Form1702EXGenerator",
    "Form1702MXData",
    "Form1702MXGenerator",
    "Form1702QData",
    "Form1702QGenerator",
    "Form1702RTData",
    "Form1702RTGenerator",
    "Form2000Data",
    "Form2000Generator",
    "Form2550MData",
    "Form2550MGenerator",
    "Form2550QData",
    "Form2550QGenerator",
    "Form2551QData",
    "Form2551QGenerator",
]
