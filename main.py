# coding:utf-8
# Author: uznEnehC
# Blog: https://noviachen.github.io/
# Python Verion: 3.6
# 感谢 Windfarer 的咕咕机 Python API (https://github.com/Windfarer/pymobird)

import config
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, redirect, url_for, session, request, flash
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import InputRequired
from pymobird import SimplePymobird

app = Flask(__name__)
bootstrap = Bootstrap(app)

# 导入配置文件
app.config.from_object(config)
ak_default = config.AK


# 获取下厨房菜谱内容(移动端URL有问题，改为使用PC端URL)
# 同时对每行内容添加换行符等，暂时不考虑图片
def get_recipe(recipe_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE'
    }
    resp = requests.get(recipe_url, headers=headers).text
    html_source = BeautifulSoup(resp, 'html.parser')

    # 菜谱标题
    recipe_name = html_source.h1.get_text().replace(' ', '').replace('\n', '')
    recipe_name = '《' + recipe_name + '》' + '\n\n'

    # 材料及用量
    recipe_materials = html_source.find(
        name='div', attrs={'class': 'ings'}).find_all('tr')
    recipe_materials_list = []
    for each_material in recipe_materials:
        things = each_material.find_all('td')
        ingredient = things[0].get_text().replace(' ', '').replace('\n', '')
        weight = things[1].get_text().replace(' ', '').replace('\n', '')
        recipe_materials_list.append(ingredient + '   ' + weight)
    recipe_materials = '【材料及用量】\n' + '\n'.join(recipe_materials_list) + '\n\n'

    # 做法及步骤
    recipe_steps = html_source.find(
        name='div', attrs={'class': 'steps'}).find_all('li')
    recipe_steps_list = []
    each_step_no = 0  # 初始化步骤号
    for step in recipe_steps:
        each_step_no = each_step_no + 1  # 步骤号
        each_step_text = step.p.get_text()  # 步骤内容
        recipe_steps_list.append(
            str(each_step_no) + ' '*3 + each_step_text + '\n')
    recipe_steps = '\n' + '\n'.join(recipe_steps_list)
    print(recipe_steps)

    try:
        recipe_tips = html_source.find(
            name='div', attrs={'class': 'tip'}).p.get_text()  # 6: 提示

    except:
        recipe_tips = '无'
    recipe_tips = '\n\n【小贴士】' + recipe_tips

    return recipe_name + \
        recipe_materials + \
        recipe_steps + \
        recipe_tips


# Flask：页面上的表单
class InputBox(FlaskForm):
    memobird_id = StringField(
        '设备编号',
        validators=[InputRequired()],
        render_kw={'placeholder': '双击按钮可得'}
    )
    ak = StringField(
        '开发者签名（选填）',
        render_kw={'placeholder': 'AK 第三方开发者签名, 留空或者自行申请'}
    )
    recipe_url = StringField(
        '下厨房链接',
        validators=[InputRequired()],
        render_kw={'placeholder': '电脑端或移动端链接均可'}
    )
    submit = SubmitField('打印菜谱')


# Flask：首页
@app.route('/', methods=['GET', 'POST'])
def index():
    form = InputBox()
    form.memobird_id.data = session.get('memobird_id')
    form.ak.data = session.get('ak')
    form.recipe_url.data = session.get('recipe_url')
    if session.get('ak') == 'akdefault':
        form.ak.data = ''
    if form.validate_on_submit():
        session['memobird_id'] = request.form['memobird_id']
        session['recipe_url'] = request.form['recipe_url']
        if request.form['ak'] == '' or request.form['ak'] is None:  # 不让 AK 显示在 URL 中
            session['ak'] = 'akdefault'
        else:
            session['ak'] = request.form['ak']
        # 获取菜谱 ID
        if session.get('recipe_url').split('/')[-1] == '':  # 判断链接结尾是否为 /
            recipe_id = session.get('recipe_url').split('/')[-2]  # 获取菜谱编号
        else:
            recipe_id = session.get('recipe_url').split('/')[-1]
        return redirect(
            url_for(
                'print_memo_paper',
                memobird_id=session.get('memobird_id'),
                ak=session.get('ak'),
                recipe_id=recipe_id,
            )
        )
    return render_template('index.html', form=form)


# Flask：打印纸条
@app.route('/print_memo_paper?memobird_id=<memobird_id>&ak=<ak>&recipe_id=<recipe_id>', methods=['GET'])
def print_memo_paper(memobird_id, ak, recipe_id):
    if ak == 'akdefault':
        ak = ak_default

    recipe_content = get_recipe(
        'https://www.xiachufang.com/recipe/' + recipe_id)
    bird = SimplePymobird(ak=ak, device_id=memobird_id)
    bird.print_text(recipe_content)

    flash(
        {
            'code': 'success',
            'msg': '菜谱机正在打印，请稍候 ...'
        }
    )

    flash(
        {
            'code': 'info',
            'msg': '如未正常打印，请检查设备编号以及开发者签名(AK)是否有误'
        }
    )

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(
        host=config.host,
        port=config.port,
        debug=config.debug
    )
