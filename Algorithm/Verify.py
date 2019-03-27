#!/usr/bin/env python3
"""
验证先关的交易策略是否生效
"""
import math
import time
import datetime
import pandas
import matplotlib.pyplot as plt
import DailyUtils.FindLowStock as FindLowStock
import Output.FileOutput as FileOutput
from Algorithm import Calculator


def verify(base_data):
    """
    根据算出分数确定交易策略是否生效
    :param base_data:
    :return:
    """
    shift_af_close = base_data['af_close'].shift(-7)
    base_data['win_percent'] = (shift_af_close - base_data['af_close']) / base_data['af_close']
    base_data['win_price'] = shift_af_close - base_data['af_close']
    # predict_win = base_data[base_data['score'] > 0]
    predict_win = pandas.DataFrame(columns=base_data.columns)
    pre_low = True
    for i in range(len(base_data)):
        if base_data.at[i, 'ma5'] > base_data.at[i, 'ma10']:
            if pre_low and base_data.at[i, 'ma3'] >= 0:
                predict_win = predict_win.append(base_data.iloc[i])
            pre_low = False
        elif base_data.at[i, 'ma5'] < base_data.at[i, 'ma10']:
            pre_low = True

    temp_win2 = pandas.DataFrame(columns=base_data.columns)
    for i in range(len(base_data)):
        if base_data.at[i, 'pma2'] < -0.04:
            pre_low = True
        if base_data.at[i, 'af_close_percent'] > 0.04 and pre_low:
            temp_win2 = temp_win2.append(base_data.iloc[i])
            pre_low = False

    # temp_win2['win_percent'].plot()

    # print("win_count")
    # print(len(base_data[base_data['win_percent'] > 0.08]))
    temp_win = base_data[base_data['win_percent'] > 0.08]
    plt.figure(1, dpi=300)
    print('real can win %d' % (len(temp_win),))
    ax1 = plt.subplot(211)
    temp_win['win_percent'].plot()
    ax2 = plt.subplot(212)
    base_data['af_close'].plot()
    # down_info = base_data[base_data['win_percent'] < 0.08]
    # ma_60_slope_down_pct = len(down_info[down_info['ma60slope'] < 0]) / len(down_info)
    # ma_30_slope_down_pct = len(down_info[down_info['ma30slope'] < 0]) / len(down_info)
    # ma_10_slope_down_pct = len(down_info[down_info['ma10slope'] < 0]) / len(down_info)
    # print("down_60_percnet: %-10.3f, down_30_percent: %-10.3f， down_10_percent: %-10.3f" % (ma_60_slope_down_pct, ma_30_slope_down_pct, ma_10_slope_down_pct))
    # down_info = down_info.sort_values(by=['win_percent'])
    # print("calculate win count")
    # print(len(predict_win))
    #
    # temp_predict_win = base_data[base_data['score'] > 0]
    # temp_predict_win['win_percent'].plot()
    # plt.scatter(base_data['score'], base_data['win_percent'])
    # plt.scatter(predict_win['score'], predict_win['win_percent'])
    # predict_win['win_percent'].plot()


def real_verify(base_data):
    shift_af_close = base_data['af_close'].shift(-5)
    base_data['win_percent'] = (shift_af_close - base_data['af_close']) / base_data['af_close']
    base_data['win_price'] = shift_af_close - base_data['af_close']

    plt.figure(1, dpi=300)
    ax1 = plt.subplot(311)
    base_data['af_close'].plot()
    ax1 = plt.subplot(312)
    base_data['score'].plot()
    temp_win = base_data[base_data['score'] > 0]
    ax2 = plt.subplot(313)
    plt.scatter(base_data['score'], base_data['win_percent'], s=1)
    # plt.scatter(temp_win['score'], temp_win['win_percent'])


def period_low_verify(base_data, index_data=None, cal_column='af_close', windows=220):
    shift_af_close = base_data[cal_column].shift(-20)
    base_data[str(windows) + '_win'] = (shift_af_close - base_data[cal_column]) / base_data[cal_column]
    if index_data is not None and not index_data.empty:
        temp_index_ma = index_data['ma50'].shift(-1)
        index_data['index_ma_50_sp'] = index_data['ma50slope'] / temp_index_ma

    result = FindLowStock.find_low_record(base_data, windows=windows)
    index_consi_result = pandas.DataFrame(columns=base_data.columns)
    if len(result) > 0 and index_data is not None:
        for i in range(len(result)):
            trade_date = result.at[i, 'trade_date']
            record = index_data[index_data['trade_date'] == trade_date]
            if record.at[0, 'index_ma_50_sp'] > 0.00:
                index_consi_result.append(result.iloc[i])

    return_rst = (index_consi_result if index_data is not None else result,
                  len(base_data[base_data[str(windows) + '_win'] > 0.08]))
    return return_rst


def batch_low_verify(data_center):
    result = pandas.DataFrame(columns=['trade_date', 'ts_code', '220_win'])
    real_win_count = pandas.DataFrame(columns=['ts_code', 'real_win_count'])
    stock_list = data_center.fetch_stock_list()
    for i in range(len(stock_list)):
        base_data = data_center.fetch_base_data_pure_database(stock_list[i][0],
                                                              begin_date='20160101', end_date='20181217')
        if not base_data.empty:
            return_result = period_low_verify(base_data, None, 'close')
            rst = return_result[0]
            rst = filter_next_up(base_data, rst)
            result = result.append(rst[['trade_date', 'ts_code', '220_win']])
            real_win_count = real_win_count.append(
                {'ts_code': base_data.at[0, 'ts_code'], 'real_win_count': return_result[1]}, ignore_index=True)
    format_percent = result['220_win'] * 100
    format_percent = format_percent.apply(lambda x: str(x) + "%")
    result['220_win'] = format_percent
    FileOutput.csv_output(None, result, '220_filter_result_filter.csv')
    FileOutput.csv_output(None, real_win_count, 'win_count_filter.csv')


def filter_next_up(base_data, filter_rst):
    filter_rst.sort_values(by=['trade_date'])
    base_data.sort_values(by=['trade_date'])
    trade_date = filter_rst['trade_date']
    # 将时间推后一天，看下一天的结果如何
    trade_date = trade_date.apply(
        lambda x: (datetime.date(int(x[0:4]), int(x[4:6]), int(x[6:8])) + datetime.timedelta(days=1))
            .strftime("%Y%m%d"))
    # 下面的方法返回一个Boolean序列
    ret_value = base_data['trade_date'].isin(trade_date)
    ret_value = base_data[ret_value.values]
    ret_value = ret_value[ret_value['pct_chg'] > 3]
    return ret_value


def high_after_low(data_center):
    """
    此段注释是后加的
    此方法用于判定历史低点之后 ，七天之内的收益如何（我感觉应该是不怎么样的，随机）
    :param data_center:
    :return:
    """
    result = pandas.DataFrame(columns=['trade_date', 'ts_code', '220_15_win'])
    real_win_count = pandas.DataFrame(columns=['ts_code', 'real_win_count'])
    stock_list = data_center.fetch_stock_list()
    for i in range(len(stock_list)):
        base_data = data_center.fetch_base_data_pure_database(stock_list[i][0],
                                                              begin_date='20160101', end_date='20181217')
        if not base_data.empty:
            # 计算逻辑
            close_shift_15 = base_data['close'].shift(-35)
            base_data['220_15_win'] = (base_data['close'] - close_shift_15) / close_shift_15
            # 下面几行代码计算一下，7天之后是否上涨已经达到了15%
            close_shift_7 = base_data['close'].shift(-7)
            base_data['7_days_up'] = (base_data['close'] - close_shift_7) / close_shift_7
            return_result = FindLowStock.find_low_record_adv(base_data, 220, 'close')
            real_count = len(return_result[return_result['220_15_win'] > 0.08])
            rst = return_result
            rst = rst[rst['7_days_up'] > 0.15]
            result = result.append(rst[['trade_date', 'ts_code', '220_15_win']])
            real_win_count = real_win_count.append(
                {'ts_code': base_data.at[0, 'ts_code'], 'real_win_count': real_count}, ignore_index=True)
    format_percent = result['220_15_win'] * 100
    format_percent = format_percent.apply(lambda x: str(x) + "%")
    result['220_15_win'] = format_percent
    FileOutput.csv_output(None, result, '220_down_15_up.csv')
    FileOutput.csv_output(None, real_win_count, 'win_count_filter_15_up.csv')


def with_15_up_buy(data_center):
    result = pandas.DataFrame(columns=['trade_date', 'ts_code', '15_win'])
    real_win_count = pandas.DataFrame(columns=['ts_code', 'real_win_count'])
    stock_list = data_center.fetch_stock_list()
    for i in range(len(stock_list)):
        base_data = data_center.fetch_base_data_pure_database(stock_list[i][0],
                                                              begin_date='20160101', end_date='20181217')
        if not base_data.empty:
            # 计算逻辑
            close_shift_7 = base_data['close'].shift(7)
            close_shift_15 = base_data['close'].shift(15)
            base_data['15_win'] = (close_shift_15 - close_shift_7) / close_shift_7
            # 下面几行代码计算一下，7天之后是否上涨已经达到了15%
            base_data['7_days_up'] = (close_shift_7 - base_data['close']) / base_data['close']
            return_result = base_data
            real_count = len(return_result[return_result['15_win'] > 0.08])
            rst = return_result
            rst = rst[rst['7_days_up'] > 0.15]
            result = result.append(rst[['trade_date', 'ts_code', '15_win']])
            real_win_count = real_win_count.append(
                {'ts_code': base_data.at[0, 'ts_code'], 'real_win_count': real_count}, ignore_index=True)
    format_percent = result['15_win'] * 100
    format_percent = format_percent.apply(lambda x: str(x) + "%")
    result['15_win'] = format_percent
    FileOutput.csv_output(None, result, '15_up.csv')
    FileOutput.csv_output(None, real_win_count, 'win_count_filter_15_up.csv')


def max_up_down_percent(base_data):
    """
    计算区间内单日的最大涨跌幅
    :param base_data: pandas.DataFrame，包含所有的股票基本信息
    :return: tuple类型，第一个元素为最大涨幅，第二个元素为最大跌幅
    """
    min_price_index = base_data['close'].idxmin()
    max_price_index = base_data['close'].idxmax()
    min_price = base_data['close'][min_price_index]
    max_price = base_data['close'][max_price_index]
    if max_price_index > min_price_index:
        max_up_percent = (max_price - min_price) / min_price
        max_down_percent = 0
        temp_max_price = base_data['close'][0]
        for i in range(1, len(base_data)):
            temp_price = base_data['close'][i]
            if temp_price < temp_max_price:
                temp_max_down_p = (temp_price - temp_max_price) / temp_max_price
                max_down_percent = temp_max_down_p if temp_max_down_p < max_down_percent else max_down_percent
            else:
                temp_max_price = temp_price
    else:
        max_down_percent = (min_price - max_price) / max_price
        max_up_percent = 0
        temp_min_price = base_data['close'][0]
        for i in range(1, len(base_data)):
            temp_price = base_data['close'][i]
            if temp_price > temp_min_price:
                temp_max_up_p = (temp_price - temp_min_price) / temp_min_price
                max_up_percent = temp_max_up_p if temp_max_up_p > max_up_percent else max_up_percent
            else:
                temp_min_price = temp_price

    return max_up_percent, max_down_percent


def curr_win_percent(data_center, begin_date, end_date):
    """
    最近几天A股主板的赚钱效应
    统计信息如下：
    1. 最大涨幅
    2. 最大跌幅
    3. 首日买入的上涨下跌频率
    :param data_center:
    :param begin_date: 计算开始日期
    :param end_date: 计算结束日期
    :return:
    """
    total_time = 0
    fetch_data_time = 0
    time1 = time.clock()
    result = pandas.DataFrame(columns=['ts_code', 'max_up_percent', 'max_down_percent'])
    real_win_count = pandas.DataFrame(columns=['ts_code', 'real_win_count'])
    stock_list = data_center.fetch_stock_list()
    total_time += (time.clock() - time1)

    win_count = 0
    all_count = 0
    for i in range(len(stock_list)):
        time_value1 = datetime.datetime.now()
        base_data = data_center.fetch_base_data_pure_database(stock_list[i][0],
                                                              begin_date=begin_date, end_date=end_date)
        fetch_data_time += (datetime.datetime.now() - time_value1).seconds
        if not base_data.empty and len(base_data) > 1:
            # 计算逻辑
            # 计算最大涨跌幅
            max_up_percent, max_down_percent = max_up_down_percent(base_data)
            if max_up_percent > 0.1 and base_data['close'][len(base_data) - 1] > base_data['close'][0]:
                win_count += 1
            all_count += 1
            result = result.append(
                {"ts_code": stock_list[i][0], "max_up_percent": max_up_percent, "max_down_percent": max_down_percent},
                ignore_index=True)
    extra_content = "win_count: %s, all_count: %s" % (win_count, all_count)
    time1 = time.clock()
    FileOutput.csv_output(None, result, 'last_days_win.csv', extra_content)
    total_time += (time.clock() - time1)
    print("cost append time %d" % total_time)
    print("fetch data time is: %d" % fetch_data_time)
    # FileOutput.csv_output(None, real_win_count, 'win_count_filter_15_up.csv')


def windows_low_buy(data_center, windows=220, begin_date='20160101', end_date='20181231', meet_first_up=False):
    """
    计算一下超跌后首日上涨后赚钱效应怎么样，但是感觉上应该是嗝屁的
    :param data_center:
    :param windows:
    :param begin_date:
    :param end_date:
    :return:
    """
    result = pandas.DataFrame(columns=['trade_date', 'ts_code', 'max_up_percent', 'max_down_percent',
                                       'target_day_percent'])
    stock_list = data_center.fetch_stock_list()

    for i in range(len(stock_list)):
        base_data = data_center.fetch_base_data_pure_database(stock_list[i][0],
                                                              begin_date=begin_date, end_date=end_date)
        if not base_data.empty and len(base_data) > 1:
            # 计算逻辑
            low_index = FindLowStock.find_low_record_adv(base_data, windows)
            thirty_after = base_data['close'].shift(-30)
            base_data['target_day_percent'] = (thirty_after - base_data['close']) / base_data['close']
            thirty_max = base_data['close'].shift(-30).rolling(30).max()
            base_data['max_up_percent'] = (thirty_max - base_data['close']) / base_data['close']
            thirty_min = base_data['close'].shift(-30).rolling(30).min()
            base_data['max_down_percent'] = (thirty_min - base_data['close']) / base_data['close']

            # 加下判定，历史低价价位之后，是否需要在首次上涨之后才去买入
            if meet_first_up:
                first_up_index = base_data['pct_chg'].shift(-1) > 0
                temp_value = base_data[low_index & first_up_index]
            else:
                temp_value = base_data[low_index]
            result = result.append(temp_value[['trade_date', 'ts_code', 'max_up_percent', 'max_down_percent',
                                               'target_day_percent']])
    file_name = "windows_low_buy_meet_up.csv" if meet_first_up else "windows_low_buy.csv"
    FileOutput.csv_output(None, result, file_name)


def slice_involve(data_center, start_number=10000):
    """
    定投的方式，看到这种方式的赚钱效应如何
    :param data_center:
    :return:
    """
    stock_list = data_center.fetch_stock_list()

    # for i in range(len(stock_list)):
    #     base_data = data_center.fetch_base_data_pure_database(stock_list[i][0],
    #                                                           begin_date=begin_date, end_date=end_date)
    #     if not base_data.empty and len(base_data) > 1:
    #         low_index = FindLowStock.find_low_record_adv(base_data)
    pass


def three_max_stock(data_center):
    """
    连续三个涨停板的股票到底如何，亟待验证
    TODO -- 验证下连续三个涨停板的股票在历史上都是怎么样的
    :param data_center:
    :return:
    """
    result = pandas.DataFrame(columns=('ts_code', 'start_date', 'one_day_pct', 'two_day_pct'))
    stock_list = data_center.fetch_stock_list()
    for i in range(len(stock_list)):
        base_data = data_center.fetch_base_data_pure_database(stock_list[i][0],
                                                              begin_date='20160101', end_date='20190130')
        if not base_data.empty and len(base_data) > 0:
            one_day_pct = base_data['pct_chg'].shift(-1)
            two_day_pct = base_data['pct_chg'].shift(-2)
            before_day_pct = base_data['pct_chg'].shift(1)
            three_up_series = (base_data['pct_chg'] > 9) & (one_day_pct > 9) & (two_day_pct > 9) & (before_day_pct < 9)

            buy_day_price = base_data['af_close'].shift(-2)
            one_day_shift_price = base_data['af_close'].shift(-3)
            two_day_shift_price = base_data['af_close'].shift(-4)
            base_data['one_day_pct'] = (one_day_shift_price - buy_day_price) / buy_day_price
            base_data['two_day_pct'] = (two_day_shift_price - buy_day_price) / buy_day_price
            base_data['start_date'] = base_data['trade_date'].shift(-2)

            # 三日涨停
            temp_three = base_data[three_up_series]
            temp_three = temp_three.loc[:, ['ts_code', 'start_date', 'one_day_pct', 'two_day_pct']]
            result = result.append(temp_three)
        # max_up_count = 0
        # for j in range(len(base_data)):
        #     if base_data.at[j, 'pct_chg'] > 9 and max_up_count < 3:
        #         max_up_count += 1
        #     if max_up_count >= 3:
        #         target_index = j + 5
        #         if target_index < len(base_data):
        #             pct_chg = (base_data.at[target_index, 'af_close'] - base_data.at[j, 'af_close']) / \
        #                     base_data.at[j, 'af_close']
        #             result = result.append({'ts_code': stock_list[i][0], 'start_date': base_data.at[j, 'trade_date'],
        #                         'wave_pct': pct_chg}, ignore_index=True)
    return result


def one_max_up(data_center, max_up_days=1):
    """
    :param max_up_days天涨停之后的情况是什么样的？
    :param max_up_days:
    :param data_center:
    :return:
    """
    result = pandas.DataFrame(columns=('ts_code', 'start_date', 'one_day_pct', 'two_day_pct'))
    stock_list = data_center.fetch_stock_list()
    for i in range(len(stock_list)):
        base_data = data_center.fetch_base_data_pure_database(stock_list[i][0],
                                                              begin_date='20160101', end_date='20190130')
        if not base_data.empty and len(base_data) > 0:
            up_index = None
            for j in range(max_up_days):
                temp_pct = base_data['pct_chg'].shift(-j)
                if j == 0:
                    up_index = temp_pct > 9
                else:
                    up_index = up_index & (temp_pct > 9)
            before_day_pct = base_data['pct_chg'].shift(1)
            up_index = up_index & (before_day_pct < 9)

            buy_day_price = base_data['af_close'].shift(-max_up_days + 1)
            one_day_shift_price = base_data['af_close'].shift(-max_up_days)
            two_day_shift_price = base_data['af_close'].shift(-max_up_days - 1)
            base_data['one_day_pct'] = (one_day_shift_price - buy_day_price) / buy_day_price
            base_data['two_day_pct'] = (two_day_shift_price - buy_day_price) / buy_day_price
            base_data['start_date'] = base_data['trade_date'].shift(-max_up_days + 1)

            # :param max_up_days天之内涨停
            temp_rst = base_data[up_index]
            temp_rst = temp_rst.loc[:, ['ts_code', 'start_date', 'one_day_pct', 'two_day_pct']]
            result = result.append(temp_rst)
    return result


def low_af_high_buy(data_center):
    """
    冲高回落之后的低谷买入，看这种情况怎么样
    :param data_center:
    :return:
    """
    result = pandas.DataFrame(columns=('ts_code', 'start_date', 'one_day_pct', 'two_day_pct'))
    stock_list = data_center.fetch_stock_list()
    for i in range(len(stock_list)):
        base_data = data_center.fetch_base_data_pure_database(stock_list[i][0],
                                                              begin_date='20160101')
        if not base_data.empty and len(base_data) > 0:
            pro_data = base_data['af_close'].rolling(window=30)


def dt_verify(data_center, stock_code=None):
    """
    定投的效果如何？
    :param stock_code:
    :param data_center:
    :return:
    """
    result = pandas.DataFrame(columns=('ts_code', 'operate_day', 'ope_price', 'ope_type', 'ope_num', 'curr_stock_num',
                                       'paper_stock_value', 'real_stock_value', 'free_value', 'every_stock_val',
                                       'continue_days'))
    if stock_code is not None:
        base_data = data_center.fetch_base_data_pure_database(stock_code,
                                                              begin_date='20160101')
        Calculator.cal_ma(base_data)

    # 初始化结果数组
    process_dt_every_ope(result, base_data, 0, stock_code, None)
    ma_bigger_zero = False
    ma_lower_zero = False
    if not base_data.empty and len(base_data) > 0:
        for i in range(len(base_data)):
            if base_data.at[i, 'ma8slope'] > 0 and not ma_bigger_zero:
                result = process_dt_every_ope(result, base_data, i, stock_code, 'buy')
                ma_bigger_zero = True
                ma_lower_zero = False
            elif base_data.at[i, 'ma8slope'] < 0 and not ma_lower_zero:
                result = process_dt_every_ope(result, base_data, i, stock_code, 'sold')
                ma_lower_zero = True
                ma_bigger_zero = False
    return result


def process_dt_every_ope(result, base_data, i, stock_code, ope_type, every_buy_value=1000):
    """
    处理定投当中的每个操作过程的结果
    这个方法当中规定了卖出规则：如果是价格高于当前价格的10%，那么就全仓卖出，如果高于当前价格的5%，那么半仓卖出
    :return:
    """
    start_val = 10000
    temp_dic = {}
    temp_dic['ts_code'] = stock_code
    if len(result) > 0:
        temp_dic['operate_day'] = base_data.at[i, 'trade_date']
        temp_dic['ope_price'] = base_data.at[i, 'close']
        temp_dic['ope_type'] = ope_type

        # 确定一下买入卖出的数量
        if ope_type == 'buy':
            last_free_value = result.at[len(result) - 1, 'free_value']
            buy_need_money = every_buy_value if every_buy_value < last_free_value else last_free_value
            # 确保操作的股数为100股的整数倍
            ope_num = int(buy_need_money // temp_dic['ope_price'] / 100)

            # 如果买入数量为100股大于buy_need_value，但是仍然有钱可以买入的话，那么买入
            if ope_num == 0:
                buy_min_money = 100 * temp_dic['ope_price']
                if buy_min_money < last_free_value:
                    ope_num = 1 # 买一手
            ope_num = ope_num * 100
        # 否则为卖出，则卖出的时候持有数量必须大于0
        elif result.at[len(result) - 1, 'curr_stock_num'] > 0:
            pre_stock_ave_price = result.at[len(result) - 1, 'every_stock_val']
            curr_stock_price = base_data.at[i, 'close']
            pct = (curr_stock_price - pre_stock_ave_price) / pre_stock_ave_price
            if pct > 0.1:
                ope_num = result.at[len(result) - 1, 'curr_stock_num']
            elif pct > 0.05:
                # 确保操作的股数为100股的整数倍
                ope_num = int(result.at[len(result) - 1, 'curr_stock_num'] / 100 / 2)
                ope_num = ope_num * 100
            else:
                ope_num = 0
        else:
            return result

        if ope_num == 0:
            return result
        temp_dic['ope_num'] = ope_num
        pre_stock_num = result.at[len(result) - 1, 'curr_stock_num'] if len(result) > 0 else 0
        temp_dic['curr_stock_num'] = pre_stock_num + temp_dic['ope_num'] if ope_type == 'buy' \
            else pre_stock_num - temp_dic['ope_num']
        temp_dic['paper_stock_value'] = temp_dic['ope_price'] * temp_dic['curr_stock_num']
        pre_free_value = result.at[len(result) - 1, 'free_value']
        temp_dic['free_value'] = (pre_free_value - temp_dic['ope_num'] * temp_dic['ope_price']) if ope_type == 'buy' \
            else (pre_free_value + temp_dic['ope_num'] * temp_dic['ope_price'])
        if ope_type == 'buy':
            this_turn_real_value = temp_dic['ope_price'] * temp_dic['ope_num']
        else:
            pre_turn_real_stock_val = result.at[len(result) - 1, 'every_stock_val']
            this_turn_real_value = -pre_turn_real_stock_val * temp_dic['ope_num']
        pre_real_stock_val = result.at[len(result) - 1, 'real_stock_value']
        temp_dic['real_stock_value'] = round(pre_real_stock_val + this_turn_real_value, 2)
        temp_dic['all_value'] = temp_dic['free_value'] + temp_dic['paper_stock_value']
        temp_dic['every_stock_val'] = temp_dic['real_stock_value'] / temp_dic['curr_stock_num'] \
            if temp_dic['curr_stock_num'] > 0 else 0
        if len(result) > 1:
            start_buy_date = result.at[1, 'operate_day']
            curr_date_str = temp_dic['operate_day']
            curr_date = datetime.date(int(curr_date_str[0:4]), int(curr_date_str[4:6]), int(curr_date_str[6:8]))
            start_date = datetime.date(int(start_buy_date[0:4]), int(start_buy_date[4:6]), int(start_buy_date[6:8]))
            date_diff = curr_date - start_date
            temp_dic['continue_days'] = date_diff.days
        else:
            temp_dic['continue_days'] = 0
        result = result.append(temp_dic, ignore_index=True)
    else:
        temp_dic['operate_day'] = '00000000'
        temp_dic['ope_price'] = 0
        temp_dic['ope_type'] = 'empty'
        temp_dic['ope_num'] = 0
        temp_dic['curr_stock_num'] = 0
        temp_dic['paper_stock_value'] = 0
        temp_dic['real_stock_value'] = 0
        temp_dic['free_value'] = start_val
        temp_dic['all_value'] = start_val
        temp_dic['continue_days'] = 0
        result = result.append(temp_dic, ignore_index=True)
    return result


def n_down_days_buy_next_sold(data_center, stock_code, down_days=3):
    """
    连续:param down_days天下跌之后当天收盘价买入，
    1. 如果第二天涨幅达到3%，那么就以这个价格卖出
    2. 如果第二天的涨幅没有达到3%，那么就以收盘价卖出
    3. 不能连续下跌的时候买入，如果某一天卖出的时候是阴线，后面继续是阴线的时候就要小心了
    这个跌幅是按照stock_base_info表格当中的pct_chg字段来判定的。
    :param down_days:
    :param data_center:
    :param stock_code:
    :return:
    """
    stock_list = data_center.fetch_stock_list()
    for j in range(len(stock_list)):
        result = pandas.DataFrame(columns=('ts_code', 'operate_day', 'ope_price', 'ope_type', 'ope_num', 'all_money',
                                           'has_stock_num', 'continue_days', 'interest_state', 'is_percent_3'))
        free_val = 10000
        has_stock = False  # 是否持仓， 模拟满仓的效果，必须第二天卖出之后才能在第三天买入
        base_data = data_center.fetch_base_data_pure_database(stock_list[j][0],
                                                              begin_date='20160101')
        stock_code = stock_list[j][0]
        if not base_data.empty:
            continue_down_days = 0
            for i in range(len(base_data)):
                if base_data.at[i, 'pct_chg'] < 0:
                    continue_down_days += 1
                else:
                    continue_down_days = 0
                # 买入操作
                if continue_down_days == down_days and not has_stock:
                    temp_dic = {
                        'ts_code': stock_code,
                        'ope_price': base_data.at[i, 'close'],
                        'operate_day': base_data.at[i, 'trade_date'],
                        'ope_type': 'buy'
                    }
                    ope_num = int(free_val // temp_dic['ope_price'] / 100)
                    ope_num = ope_num * 100
                    temp_dic['ope_num'] = ope_num
                    temp_dic['has_stock_num'] = ope_num
                    temp_dic['all_money'] = free_val
                    free_val -= ope_num * temp_dic['ope_price']
                    has_stock = True
                    result = result.append(temp_dic, ignore_index=True)
                # 是否刚刚买入的？
                if not result.empty:
                    is_curr_buy = True if result.at[len(result) - 1, 'operate_day'] == base_data.at[i, 'trade_date'] \
                        else False
                else:
                    is_curr_buy = True
                if has_stock and not is_curr_buy:
                    buy_price = result.at[len(result) - 1, 'ope_price']
                    ope_num = result.at[len(result) - 1, 'ope_num']
                    curr_price = base_data.at[i, 'high']
                    temp_dic = {
                        'ts_code': stock_code,
                        'operate_day': base_data.at[i, 'trade_date'],
                        'ope_type': 'sold'
                    }
                    # 涨幅达到了3%
                    if (curr_price / buy_price) > 1.03:
                        sold_price = buy_price * 1.03
                        sold_money = ope_num * sold_price
                        temp_dic['is_percent_3'] = "Yes"
                    # 涨幅没有达到3%， 以收盘价卖出
                    else:
                        sold_price = base_data.at[i, 'close']
                        sold_money = sold_price * ope_num
                        temp_dic['is_percent_3'] = ''
                    free_val += sold_money
                    # 统计一下数据
                    temp_dic['ope_price'] = sold_price
                    temp_dic['has_stock_num'] = 0
                    temp_dic['all_money'] = free_val
                    temp_dic['interest_state'] = '' if free_val > result.at[len(result) - 1, 'all_money'] else 'lost'
                    result = result.append(temp_dic, ignore_index=True)
                    has_stock = False
        if not result.empty:
            temp_sold_rst = result[result['ope_type'] == 'sold']
            win_count = len(temp_sold_rst[temp_sold_rst['interest_state'] != 'lost'])
            target_acc_num = len(result[result['is_percent_3'] == 'Yes'])
            sold_num = len(result[result['ope_type'] == 'sold'])
            win_percent = win_count / sold_num
            target_acc_pct = target_acc_num / sold_num
        else:
            win_percent = 0
            target_acc_pct = 0
        extra_content = 'win_percent is ' + str(win_percent)
        extra_content = extra_content + '\n' + 'target_acc_pct is ' + str(target_acc_pct)
        if not result.empty:
            FileOutput.csv_output(None, result, 'down_3_buy_verify_' + stock_list[j][0] + '.csv',
                                  extra_content=extra_content, spe_dir_name='down_3_buy')
    # if stock_code is not None:
    #     base_data = data_center.fetch_base_data_pure_database(stock_code,
    #                                                           begin_date='20160101')
    #     if not base_data.empty:
    #         continue_down_days = 0
    #         for i in range(len(base_data)):
    #             if base_data.at[i, 'pct_chg'] < 0:
    #                 continue_down_days += 1
    #             else:
    #                 continue_down_days = 0
    #             # 买入操作
    #             if continue_down_days == down_days and not has_stock:
    #                 temp_dic = {
    #                     'ts_code': stock_code,
    #                     'ope_price': base_data.at[i, 'close'],
    #                     'operate_day': base_data.at[i, 'trade_date'],
    #                     'ope_type': 'buy'
    #                 }
    #                 ope_num = int(free_val // temp_dic['ope_price'] / 100)
    #                 ope_num = ope_num * 100
    #                 temp_dic['ope_num'] = ope_num
    #                 temp_dic['has_stock_num'] = ope_num
    #                 temp_dic['all_money'] = free_val
    #                 free_val -= ope_num * temp_dic['ope_price']
    #                 has_stock = True
    #                 result = result.append(temp_dic, ignore_index=True)
    #             # 是否刚刚买入的？
    #             if not result.empty:
    #                 is_curr_buy = True if result.at[len(result) - 1, 'operate_day'] == base_data.at[i, 'trade_date'] \
    #                     else False
    #             else:
    #                 is_curr_buy = True
    #             if has_stock and not is_curr_buy:
    #                 buy_price = result.at[len(result) - 1, 'ope_price']
    #                 ope_num = result.at[len(result) - 1, 'ope_num']
    #                 curr_price = base_data.at[i, 'high']
    #                 temp_dic = {
    #                     'ts_code': stock_code,
    #                     'operate_day': base_data.at[i, 'trade_date'],
    #                     'ope_type': 'sold'
    #                 }
    #                 # 涨幅达到了3%
    #                 if (curr_price / buy_price) > 1.03:
    #                     sold_price = buy_price * 1.03
    #                     sold_money = ope_num * sold_price
    #                 # 涨幅没有达到3%， 以收盘价卖出
    #                 else:
    #                     sold_price = base_data.at[i, 'close']
    #                     sold_money = sold_price * ope_num
    #                 free_val += sold_money
    #                 # 统计一下数据
    #                 temp_dic['ope_price'] = sold_price
    #                 temp_dic['has_stock_num'] = 0
    #                 temp_dic['all_money'] = free_val
    #                 temp_dic['interest_state'] = '' if free_val > result.at[len(result) - 1, 'all_money'] else 'lost'
    #                 result = result.append(temp_dic, ignore_index=True)
    #                 has_stock = False
    # 统计一下获利百分比

    # return result, 'win_percent is ' + str(win_percent)


def n_green_days_buy_next_sold(data_center, stock_code, down_days=4):
    """
    连续:param down_days天下跌之后(此处不是指当天收盘价比前一天低，而是指当天收盘价比当天开盘价低)当天收盘价买入，
    1. 如果第二天涨幅达到3%，那么就以这个价格卖出
    2. 如果第二天的涨幅没有达到3%，那么就以收盘价卖出
    3. 不能连续下跌的时候买入，如果某一天卖出的时候是阴线，后面继续是阴线的时候就要小心了
    这个跌幅是按照stock_base_info表格当中的pct_chg字段来判定的。
    :param down_days:
    :param data_center:
    :param stock_code:
    :return:
    """
    stock_list = data_center.fetch_stock_list()
    for j in range(len(stock_list)):
        result = pandas.DataFrame(columns=('ts_code', 'operate_day', 'ope_price', 'ope_type', 'ope_num', 'all_money',
                                           'has_stock_num', 'continue_days', 'interest_state', 'is_percent_3'))
        free_val = 10000
        has_stock = False  # 是否持仓， 模拟满仓的效果，必须第二天卖出之后才能在第三天买入
        stock_code = stock_list[j][0]
        base_data = data_center.fetch_base_data_pure_database(stock_code,
                                                              begin_date='20160101')
        if not base_data.empty:
            continue_down_days = 0
            for i in range(len(base_data)):
                if base_data.at[i, 'close'] < base_data.at[i, 'open']:
                    continue_down_days += 1
                else:
                    continue_down_days = 0
                # 买入操作
                if continue_down_days == down_days and not has_stock:
                    temp_dic = {
                        'ts_code': stock_code,
                        'ope_price': base_data.at[i, 'close'],
                        'operate_day': base_data.at[i, 'trade_date'],
                        'ope_type': 'buy'
                    }
                    ope_num = int(free_val // temp_dic['ope_price'] / 100)
                    ope_num = ope_num * 100
                    temp_dic['ope_num'] = ope_num
                    temp_dic['has_stock_num'] = ope_num
                    temp_dic['all_money'] = free_val
                    free_val -= ope_num * temp_dic['ope_price']
                    has_stock = True
                    result = result.append(temp_dic, ignore_index=True)
                # 是否刚刚买入的？
                if not result.empty:
                    is_curr_buy = True if result.at[len(result) - 1, 'operate_day'] == base_data.at[i, 'trade_date'] \
                        else False
                else:
                    is_curr_buy = True
                if has_stock and not is_curr_buy:
                    buy_price = result.at[len(result) - 1, 'ope_price']
                    ope_num = result.at[len(result) - 1, 'ope_num']
                    curr_price = base_data.at[i, 'high']
                    temp_dic = {
                        'ts_code': stock_code,
                        'operate_day': base_data.at[i, 'trade_date'],
                        'ope_type': 'sold'
                    }
                    # 涨幅达到了3%
                    if (curr_price / buy_price) > 1.03:
                        sold_price = buy_price * 1.03
                        sold_money = ope_num * sold_price
                        is_target_percent = True
                    # 涨幅没有达到3%， 以收盘价卖出
                    else:
                        sold_price = base_data.at[i, 'close']
                        sold_money = sold_price * ope_num
                        is_target_percent = False
                    free_val += sold_money
                    # 统计一下数据
                    temp_dic['ope_price'] = sold_price
                    temp_dic['has_stock_num'] = 0
                    temp_dic['all_money'] = free_val
                    temp_dic['is_percent_3'] = 'Yes' if is_target_percent else ''
                    temp_dic['interest_state'] = '' if free_val > result.at[len(result) - 1, 'all_money'] else 'lost'
                    result = result.append(temp_dic, ignore_index=True)
                    has_stock = False
        # 统计一下获利百分比
        if not result.empty:
            temp_sold_rst = result[result['ope_type'] == 'sold']
            win_count = len(temp_sold_rst[temp_sold_rst['interest_state'] != 'lost'])
            target_acc_num = len(result[result['is_percent_3'] == 'Yes'])
            sold_num = len(result[result['ope_type'] == 'sold'])
            win_percent = win_count / sold_num
            target_acc_pct = target_acc_num / sold_num
        else:
            win_percent = 0
            target_acc_pct = 0
        extra_content = 'win_percent is ' + str(win_percent)
        extra_content = extra_content + '\n' + 'target_acc_pct is ' + str(target_acc_pct)
        if not result.empty:
            FileOutput.csv_output(None, result, 'green_4_buy_verify_' + stock_list[j][0] + '.csv',
                                  extra_content=extra_content, spe_dir_name='green_4_buy')
    # if stock_code is not None:
    #     result = pandas.DataFrame(columns=('ts_code', 'operate_day', 'ope_price', 'ope_type', 'ope_num', 'all_money',
    #                                        'has_stock_num', 'continue_days', 'interest_state'))
    #     free_val = 10000
    #     has_stock = False  # 是否持仓， 模拟满仓的效果，必须第二天卖出之后才能在第三天买入
    #     base_data = data_center.fetch_base_data_pure_database(stock_code,
    #                                                           begin_date='20160101')
    #     if not base_data.empty:
    #         continue_down_days = 0
    #         for i in range(len(base_data)):
    #             if base_data.at[i, 'close'] < base_data.at[i, 'open']:
    #                 continue_down_days += 1
    #             else:
    #                 continue_down_days = 0
    #             # 买入操作
    #             if continue_down_days == down_days and not has_stock:
    #                 temp_dic = {
    #                     'ts_code': stock_code,
    #                     'ope_price': base_data.at[i, 'close'],
    #                     'operate_day': base_data.at[i, 'trade_date'],
    #                     'ope_type': 'buy'
    #                 }
    #                 ope_num = int(free_val // temp_dic['ope_price'] / 100)
    #                 ope_num = ope_num * 100
    #                 temp_dic['ope_num'] = ope_num
    #                 temp_dic['has_stock_num'] = ope_num
    #                 temp_dic['all_money'] = free_val
    #                 free_val -= ope_num * temp_dic['ope_price']
    #                 has_stock = True
    #                 result = result.append(temp_dic, ignore_index=True)
    #             # 是否刚刚买入的？
    #             if not result.empty:
    #                 is_curr_buy = True if result.at[len(result) - 1, 'operate_day'] == base_data.at[i, 'trade_date'] \
    #                     else False
    #             else:
    #                 is_curr_buy = True
    #             if has_stock and not is_curr_buy:
    #                 buy_price = result.at[len(result) - 1, 'ope_price']
    #                 ope_num = result.at[len(result) - 1, 'ope_num']
    #                 curr_price = base_data.at[i, 'high']
    #                 temp_dic = {
    #                     'ts_code': stock_code,
    #                     'operate_day': base_data.at[i, 'trade_date'],
    #                     'ope_type': 'sold'
    #                 }
    #                 # 涨幅达到了3%
    #                 if (curr_price / buy_price) > 1.03:
    #                     sold_price = buy_price * 1.03
    #                     sold_money = ope_num * sold_price
    #                 # 涨幅没有达到3%， 以收盘价卖出
    #                 else:
    #                     sold_price = base_data.at[i, 'close']
    #                     sold_money = sold_price * ope_num
    #                 free_val += sold_money
    #                 # 统计一下数据
    #                 temp_dic['ope_price'] = sold_price
    #                 temp_dic['has_stock_num'] = 0
    #                 temp_dic['all_money'] = free_val
    #                 temp_dic['interest_state'] = '' if free_val > result.at[len(result) - 1, 'all_money'] else 'lost'
    #                 result = result.append(temp_dic, ignore_index=True)
    #                 has_stock = False
    # # 统计一下获利百分比
    # if not result.empty:
    #     win_count = len(result[result['interest_state'] != 'lost'])
    #     win_percent = win_count / len(result)
    # else:
    #     win_percent = 0
    # return result, 'win_percent is ' + str(win_percent)


def n_green_days_two_red_buy_next_sold(data_center, stock_code, down_days=4):
    """
    连续:param down_days天下跌之后(此处不是指当天收盘价比前一天低，而是指当天收盘价比当天开盘价低),然后连续两天红线，
    以第二天红线的收盘价买入
    1. 如果第二天涨幅达到3%，那么就以这个价格卖出
    2. 如果第二天的涨幅没有达到3%，那么就以收盘价卖出
    3. 不能连续下跌的时候买入，如果某一天卖出的时候是阴线，后面继续是阴线的时候就要小心了
    这个跌幅是按照stock_base_info表格当中的pct_chg字段来判定的。
    :param down_days:
    :param data_center:
    :param stock_code:
    :return:
    """
    stock_list = data_center.fetch_stock_list()
    for j in range(len(stock_list)):
        result = pandas.DataFrame(columns=('ts_code', 'operate_day', 'ope_price', 'ope_type', 'ope_num', 'all_money',
                                           'has_stock_num', 'continue_days', 'interest_state', 'is_percent_3'))
        free_val = 10000
        has_stock = False  # 是否持仓， 模拟满仓的效果，必须第二天卖出之后才能在第三天买入
        stock_code = stock_list[j][0]
        base_data = data_center.fetch_base_data_pure_database(stock_code,
                                                              begin_date='20160101')
        if not base_data.empty:
            continue_down_days = 0
            red_days = 0
            for i in range(len(base_data)):
                if base_data.at[i, 'close'] < base_data.at[i, 'open']:
                    if red_days > 0:
                        continue_down_days = 1
                        red_days = 0
                    else:
                        continue_down_days += 1
                        red_days = 0
                else:
                    if red_days < 2 and continue_down_days >= down_days:
                        red_days += 1
                    elif continue_down_days >= down_days and red_days > 2:
                        continue_down_days = 0
                        red_days = 0
                    else:
                        red_days = 0
                        continue_down_days = 0
                # 买入操作
                if continue_down_days >= down_days and red_days == 2 and not has_stock:
                    temp_dic = {
                        'ts_code': stock_code,
                        'ope_price': base_data.at[i, 'close'],
                        'operate_day': base_data.at[i, 'trade_date'],
                        'ope_type': 'buy'
                    }
                    ope_num = int(free_val // temp_dic['ope_price'] / 100)
                    ope_num = ope_num * 100
                    temp_dic['ope_num'] = ope_num
                    temp_dic['has_stock_num'] = ope_num
                    temp_dic['all_money'] = free_val
                    free_val -= ope_num * temp_dic['ope_price']
                    has_stock = True
                    result = result.append(temp_dic, ignore_index=True)
                # 是否刚刚买入的？
                if not result.empty:
                    is_curr_buy = True if result.at[len(result) - 1, 'operate_day'] == base_data.at[i, 'trade_date'] \
                        else False
                else:
                    is_curr_buy = True
                if has_stock and not is_curr_buy:
                    # 加项：如果是继续上涨当中的话 ，那么就可以不必卖出，等待利润增长
                    if base_data.at[i, 'close'] < base_data.at[i, 'open']:
                        buy_price = result.at[len(result) - 1, 'ope_price']
                        ope_num = result.at[len(result) - 1, 'ope_num']
                        curr_price = base_data.at[i, 'high']
                        temp_dic = {
                            'ts_code': stock_code,
                            'operate_day': base_data.at[i, 'trade_date'],
                            'ope_type': 'sold'
                        }
                        # 涨幅达到了3%
                        if (curr_price / buy_price) > 1.03:
                            sold_price = buy_price * 1.03
                            sold_money = ope_num * sold_price
                            is_target_percent = True
                        # 涨幅没有达到3%， 以收盘价卖出
                        else:
                            sold_price = base_data.at[i, 'close']
                            sold_money = sold_price * ope_num
                            is_target_percent = False
                        free_val += sold_money
                        # 统计一下数据
                        temp_dic['ope_price'] = sold_price
                        temp_dic['has_stock_num'] = 0
                        temp_dic['all_money'] = free_val
                        temp_dic['is_percent_3'] = 'Yes' if is_target_percent else ''
                        temp_dic['interest_state'] = '' if free_val > result.at[
                            len(result) - 1, 'all_money'] else 'lost'
                        result = result.append(temp_dic, ignore_index=True)
                        has_stock = False
        # 统计一下获利百分比
        if not result.empty:
            temp_sold_rst = result[result['ope_type'] == 'sold']
            win_count = len(temp_sold_rst[temp_sold_rst['interest_state'] != 'lost'])
            target_acc_num = len(result[result['is_percent_3'] == 'Yes'])
            sold_num = len(result[result['ope_type'] == 'sold'])
            win_percent = win_count / sold_num
            target_acc_pct = target_acc_num / sold_num
        else:
            win_percent = 0
            target_acc_pct = 0
        extra_content = 'win_percent is ' + str(win_percent)
        extra_content = extra_content + '\n' + 'target_acc_pct is ' + str(target_acc_pct)
        if not result.empty:
            FileOutput.csv_output(None, result, 'green_3_red_2_buy_verify_' + stock_list[j][0] + '.csv',
                                  extra_content=extra_content, spe_dir_name='green_3_red_2_buy_01')


def n_max_up_buy_verify(data_center):
    result = pandas.DataFrame(columns=('ts_code', 'name', 'trade_date', 'up_pct', 'is_win', 'is_buy_max',
                                       'is_sold_max', 'is_7_percent', 'is_10_percent'))
    stock_list = data_center.fetch_stock_list()

    # 统计一下第一天成功封涨停而第二天封涨停失败的概率（此处封涨停是指上涨超过9%）
    ok_num = 0  # 成功封涨停的天数
    fail_num = 0  # 第二天开盘成功封涨停但是尾盘封涨停失败的天数
    for i in range(len(stock_list)):
        base_data = data_center.fetch_base_data_pure_database(stock_list[i][0],
                                                              begin_date='20160101')
        if not base_data.empty:
            base_data.loc[:, 'next_pct_chg'] = base_data['pct_chg'].shift(-1)
            base_data.loc[:, 'pre_pct_chg'] = base_data['pct_chg'].shift(1)
            base_data.loc[:, 'next_open'] = base_data['open'].shift(-1)
            base_data.loc[:, 'next_high'] = base_data['high'].shift(-1)
            base_data.loc[:, 'next_close'] = base_data['close'].shift(-1)
            base_data.loc[:, 'open_pct'] = (base_data['next_open'] - base_data['close']) / base_data['close']
            base_data.loc[:, 'high_pct'] = (base_data['next_high'] - base_data['high']) / base_data['high']
            ok_index = (base_data['pct_chg'] > 9) & (base_data['next_pct_chg'] > 9) & (base_data['pre_pct_chg'] < 9)
            fail_index = (base_data['pct_chg'] > 9) & (base_data['next_pct_chg'] < 9) & (base_data['high_pct'] > 0.09)\
                         & (base_data['pre_pct_chg'] < 9)
            ok_num += len(ok_index[ok_index])
            fail_num += len(fail_index[fail_index])
            buy_index = ok_index.shift(1)
            buy_index[0] = False
            # buy_index[1] = False
            sold_index = ok_index.shift(2)
            sold_index[0] = False
            sold_index[1] = False
            # sold_index[2] = False
            temp = pandas.DataFrame(columns=('ts_code', 'name', 'trade_date', 'up_pct', 'get_target', 'is_win',
                                             'is_buy_max', 'is_sold_max', 'is_7_percent', 'is_10_percent'))
            buy_data = base_data[buy_index]
            buy_data.index = range(len(buy_data))
            is_buy_max = buy_data['open'] == buy_data['high']
            sold_data = base_data[sold_index]
            sold_data.index = range(len(sold_data))
            is_sold_max = sold_data['open'] == sold_data['high']
            up_pct = (sold_data['open'] - buy_data['open']) / buy_data['open']
            temp.loc[:, 'trade_date'] = sold_data['trade_date']
            temp.loc[:, 'up_pct'] = up_pct
            temp.loc[:, 'is_buy_max'] = is_buy_max
            temp.loc[:, 'is_sold_max'] = is_sold_max
            temp.loc[:, 'is_win'] = temp['up_pct'] > 0
            temp.loc[:, 'get_target'] = temp['up_pct'] > 0.03
            temp.loc[:, 'ts_code'] = stock_list[i][0]
            temp.loc[:, 'name'] = stock_list[i][2]
            temp.loc[:, 'is_7_percent'] = up_pct >= 0.07
            temp.loc[:, 'is_10_percent'] = up_pct >= 0.1
            result = result.append(temp)
    if not result.empty:
        # 统计信息
        win_count = len(result[result['is_win']])
        win_percent = win_count / len(result)
        target_achieve_count = len(result[result['get_target']])
        target_achieve_percent = target_achieve_count / len(result)
        extra_content = "win percent is " + str(win_percent) + "\n"
        extra_content += "target ace percent is " + str(target_achieve_percent) + "\n"

        seven_percent_count = len(result[result['is_7_percent']]) / len(result)
        extra_content += '7 percent achieve is ' + str(seven_percent_count) + "\n"
        ten_percent_count = len(result[result['is_10_percent']]) / len(result)
        extra_content += '10 percent achieve is ' + str(ten_percent_count) + "\n"

        # 统计一下成功封涨停的概率（第二天开盘）
        success_up_percent = ok_num / (ok_num + fail_num)
        extra_content += "success max up is " + str(success_up_percent)
        FileOutput.csv_output(None, result, 'max_buy_verify_04.csv', extra_content=extra_content)


def recent_two_max_up_rate(data_center):
    """
    最近30天之内连续涨停的概率以及连续涨停后下一天盈利的概率
    :param data_center:
    :return:
    """
    result = pandas.DataFrame(columns=('ts_code', 'name', 'trade_date', 'up_pct', 'is_win', 'is_buy_max',
                                       'is_sold_max', 'is_7_percent', 'is_10_percent'))
    stock_list = data_center.fetch_stock_list()

    # 统计一下第一天成功封涨停而第二天封涨停失败的概率（此处封涨停是指上涨超过9%）
    ok_num = 0  # 成功封涨停的天数
    fail_num = 0  # 第二天开盘成功封涨停但是尾盘封涨停失败的天数
    for i in range(len(stock_list)):
        base_data = data_center.fetch_base_data_pure_database(stock_list[i][0],
                                                              begin_date='20160101')
        if not base_data.empty:
            base_data.loc[:, 'next_pct_chg'] = base_data['pct_chg'].shift(-1)
            base_data.loc[:, 'pre_pct_chg'] = base_data['pct_chg'].shift(1)
            base_data.loc[:, 'next_open'] = base_data['open'].shift(-1)
            base_data.loc[:, 'next_high'] = base_data['high'].shift(-1)
            base_data.loc[:, 'next_close'] = base_data['close'].shift(-1)
            base_data.loc[:, 'open_pct'] = (base_data['next_open'] - base_data['close']) / base_data['close']
            base_data.loc[:, 'high_pct'] = (base_data['next_high'] - base_data['high']) / base_data['high']
            ok_index = (base_data['pct_chg'] > 9) & (base_data['next_pct_chg'] > 9) & (base_data['pre_pct_chg'] < 9)
            fail_index = (base_data['pct_chg'] > 9) & (base_data['next_pct_chg'] < 9) & (base_data['high_pct'] > 0.09) \
                         & (base_data['pre_pct_chg'] < 9)
            ok_num += len(ok_index[ok_index])
            fail_num += len(fail_index[fail_index])
            buy_index = ok_index.shift(1)
            buy_index[0] = False
            # buy_index[1] = False
            sold_index = ok_index.shift(2)
            sold_index[0] = False
            sold_index[1] = False
            # sold_index[2] = False
            temp = pandas.DataFrame(columns=('ts_code', 'name', 'trade_date', 'up_pct', 'get_target', 'is_win',
                                             'is_buy_max', 'is_sold_max', 'is_7_percent', 'is_10_percent'))
            buy_data = base_data[buy_index]
            buy_data.index = range(len(buy_data))
            is_buy_max = buy_data['open'] == buy_data['high']
            sold_data = base_data[sold_index]
            sold_data.index = range(len(sold_data))
            is_sold_max = sold_data['open'] == sold_data['high']
            up_pct = (sold_data['open'] - buy_data['open']) / buy_data['open']
            temp.loc[:, 'trade_date'] = sold_data['trade_date']
            temp.loc[:, 'up_pct'] = up_pct
            temp.loc[:, 'is_buy_max'] = is_buy_max
            temp.loc[:, 'is_sold_max'] = is_sold_max
            temp.loc[:, 'is_win'] = temp['up_pct'] > 0
            temp.loc[:, 'get_target'] = temp['up_pct'] > 0.03
            temp.loc[:, 'ts_code'] = stock_list[i][0]
            temp.loc[:, 'name'] = stock_list[i][2]
            temp.loc[:, 'is_7_percent'] = up_pct >= 0.07
            temp.loc[:, 'is_10_percent'] = up_pct >= 0.1
            result = result.append(temp)
    if not result.empty:
        # 统计信息
        win_count = len(result[result['is_win']])
        win_percent = win_count / len(result)
        target_achieve_count = len(result[result['get_target']])
        target_achieve_percent = target_achieve_count / len(result)
        extra_content = "win percent is " + str(win_percent) + "\n"
        extra_content += "target ace percent is " + str(target_achieve_percent) + "\n"

        seven_percent_count = len(result[result['is_7_percent']]) / len(result)
        extra_content += '7 percent achieve is ' + str(seven_percent_count) + "\n"
        ten_percent_count = len(result[result['is_10_percent']]) / len(result)
        extra_content += '10 percent achieve is ' + str(ten_percent_count) + "\n"

        # 统计一下成功封涨停的概率（第二天开盘）
        success_up_percent = ok_num / (ok_num + fail_num)
        extra_content += "success max up is " + str(success_up_percent)
        FileOutput.csv_output(None, result, 'max_buy_verify_04.csv', extra_content=extra_content)
