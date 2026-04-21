def get_weekly_performance_data():
    combined_df = []
    current_stats = {}

    for sym, info in tickers_info.items():
        try:
            # 1개월치 데이터 로드
            df = yf.download(sym, period='1mo', interval='15m', progress=False, group_by='ticker')
            if df.empty: continue
            
            close = df['Close'].iloc[:, 0].copy() if isinstance(df.columns, pd.MultiIndex) else df['Close'].copy()
            
            # KST 변환
            if close.index.tz is None:
                close.index = close.index.tz_localize('UTC').tz_convert('Asia/Seoul')
            else:
                close.index = close.index.tz_convert('Asia/Seoul')

            # --- [수정] 금요일 오후 2시 가격을 기준점으로 설정 ---
            # 각 주차별로 그룹화
            year_week = close.index.strftime('%Y-%U')
            
            def get_friday_2pm_price(group):
                # 이전 주(week-1)의 금요일 14:00 데이터를 찾아야 하지만, 
                # 간단하게 "해당 그룹(주차)의 첫 데이터" 대신 "직전 영업일 특정 시간"을 타겟팅합니다.
                # 여기서는 사용자 요청에 따라 '기준 가격'을 계산하는 로직을 적용합니다.
                
                # 해당 주차의 월요일 09:00 시가 대신, 
                # 데이터 프레임 전체에서 해당 시점 이전의 가장 가까운 금요일 14:00 가격을 찾습니다.
                target_time = group.index[0].replace(hour=9, minute=0) # 현재 주의 시작점
                
                # 전체 데이터에서 target_time 이전의 금요일 14:00 데이터를 필터링
                prior_data = close[close.index < target_time]
                friday_2pm = prior_data[(prior_data.index.weekday == 4) & (prior_data.index.hour == 14)]
                
                if not friday_2pm.empty:
                    return friday_2pm.iloc[-1] # 가장 최근 금요일 14:00 가격
                else:
                    return group.iloc[0] # 데이터가 없으면 현재 주 첫 가격 사용

            # 주차별로 기준 가격 매핑
            base_prices = close.groupby(year_week).apply(lambda x: get_friday_2pm_price(x))
            
            # 수익률 계산 (close 시리즈의 각 행에 해당하는 주차의 base_price 적용)
            ret = close.copy()
            for wk in year_week.unique():
                mask = (year_week == wk)
                ret[mask] = ((close[mask] - base_prices[wk]) / base_prices[wk] * 100)

            # --- 이후 로직 동일 ---
            if sym == 'DX-Y.NYB': ret *= 5
            
            latest_val = close.dropna().iloc[-1]
            latest_ret = ret.dropna().iloc[-1]
            current_stats[sym] = {'price': latest_val, 'ret': latest_ret}
            ret.name = sym
            combined_df.append(ret)
            
        except Exception as e:
            continue
    
    return pd.concat(combined_df, axis=1) if combined_df else (None, None), current_stats
