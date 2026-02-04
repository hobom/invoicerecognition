"""
SQL执行服务
提供SQL查询执行功能，支持SELECT和DML操作
"""
from db import SessionLocal, engine
from sqlalchemy import text
import json


class SQLService:
    """SQL执行服务类"""
    
    @staticmethod
    def execute_query(sql: str):
        """
        执行SQL查询
        
        Args:
            sql: SQL语句
            
        Returns:
            dict: 包含执行结果的字典
                - 对于SELECT查询：返回结果集列表
                - 对于DML操作：返回受影响的行数
                - 如果出错：返回错误信息
        """
        db = SessionLocal()
        try:
            # 使用text()包装SQL语句，支持参数化查询
            result = db.execute(text(sql))
            
            # 判断SQL类型
            sql_lower = sql.strip().lower()
            if sql_lower.startswith('select'):
                # SELECT查询：返回结果集
                rows = result.fetchall()
                # 将结果转换为字典列表
                columns = result.keys()
                results = []
                for row in rows:
                    row_dict = {}
                    for idx, col in enumerate(columns):
                        value = row[idx]
                        # 处理JSON类型字段
                        if isinstance(value, (dict, list)):
                            row_dict[col] = value
                        else:
                            row_dict[col] = value
                    results.append(row_dict)
                return {
                    'success': True,
                    'type': 'select',
                    'data': results,
                    'count': len(results)
                }
            else:
                # DML操作：提交事务并返回受影响行数
                db.commit()
                affected_rows = result.rowcount
                return {
                    'success': True,
                    'type': 'dml',
                    'affected_rows': affected_rows
                }
        except Exception as e:
            db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            db.close()
    
    @staticmethod
    def execute_safe_query(sql: str, params: dict = None):
        """
        执行参数化SQL查询（防止SQL注入）
        
        Args:
            sql: SQL语句（可使用:param_name占位符）
            params: 参数字典
            
        Returns:
            dict: 执行结果
        """
        db = SessionLocal()
        try:
            if params:
                result = db.execute(text(sql), params)
            else:
                result = db.execute(text(sql))
            
            sql_lower = sql.strip().lower()
            if sql_lower.startswith('select'):
                rows = result.fetchall()
                columns = result.keys()
                results = []
                for row in rows:
                    row_dict = {}
                    for idx, col in enumerate(columns):
                        value = row[idx]
                        if isinstance(value, (dict, list)):
                            row_dict[col] = value
                        else:
                            row_dict[col] = value
                    results.append(row_dict)
                return {
                    'success': True,
                    'type': 'select',
                    'data': results,
                    'count': len(results)
                }
            else:
                db.commit()
                return {
                    'success': True,
                    'type': 'dml',
                    'affected_rows': result.rowcount
                }
        except Exception as e:
            db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            db.close()
