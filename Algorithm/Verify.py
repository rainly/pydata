#!/usr/bin/env python3
"""
验证先关的交易策略是否生效
"""
import math
import datetime
import pandas
import matplotlib.pyplot as plt
import DailyUtils.FindLowStock as FindLowStock
import Output.FileOutput as FileOutput


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
            return_result = period_low_verify(base_data  , None, 'close')
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
    trade_date = trade_date.apply(lambda x: (datetime.date(int(x[0:4]), int(x[4:6]), int(x[6:8])) + datetime.timedelta(days=1))
                     .strftime("%Y%m%d"))
    # 下面的方法返回一个Boolean序列
    ret_value = base_data['trade_date'].isin(trade_date)
    ret_value = base_data[ret_value.values]
    ret_value = ret_value[ret_value['pct_chg'] > 3]
    return ret_value
