from legistar.base.form import Form


class Form(Form):
    skip_first_submit = True
    TableClass = 'legistar.base.table.Table'
