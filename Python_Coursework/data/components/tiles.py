from .. import config as c
from ..basetypes import Vector2, Game_Object, State_Machine, State, Entity, Rectangle
from .. import sprites
from .. import sounds
from ..utils import accelerate
from .. import level
import pygame as pg

"""定义瓷砖类"""
class Collider_Rect(Game_Object):
    def __init__(self, rect):
        super(Collider_Rect, self).__init__(rect)

class Question(Game_Object):
    """问题砖块"""
    def __init__(self, rect, contents):
        super(Question, self).__init__(rect)    # 继承矩形类
        self.contents = contents

        self.animation = self.Animation(self.pos.y)
        self.state_machine = State_Machine(self.Closed_State(), self)

    def update(self):
        self.state_machine.update()

    def draw(self, pos):
        c.screen.blit(sprites.tile_set, (pos.x, pos.y), self.animation.current_sprite)

    class Animation():
        """包含该类的特定动画变量和函数"""
        def __init__(self, start_height):
            self.current_sprite = sprites.Q_BLOCK_CLOSED[0]

            self.outer_timer = c.INITIAL_TIMER_VALUE
            self.inner_timer = c.INITIAL_TIMER_VALUE
            self.closed_frame = 0
            self.closed_frames = [0, 1, 2, 1, 0]

            self.start_height = start_height
            self.bounce_iteration = 0
            self.new_y = start_height

        def closed_anim(self):
            """未打开时的动画"""
            self.current_sprite = sprites.Q_BLOCK_CLOSED[self.closed_frames[self.closed_frame]]
            self.outer_timer += c.delta_time
            if self.outer_timer > 20 * c.delta_time:
                self.inner_timer += c.delta_time
                if self.inner_timer > 6 * c.delta_time:
                    self.closed_frame += 1
                    self.inner_timer = 0

                if self.closed_frame == 5:
                    self.outer_timer = 0
                    self.closed_frame = 0

        def bounce_anim(self):
            """弹跳时的动画"""
            self.new_y = self.start_height - self.bounce_anim_function(self.bounce_iteration)
            self.bounce_iteration += 4
            
        def bounce_anim_function(self, bounce_iteration):
            """根据数学函数返回新的 y 位置"""
            return -abs(bounce_iteration - 24) + 24

    class Closed_State(State):
        """尚未打开时的状态"""
        def on_event(self, event):
            if event == 'bounce':
                return Question.Bounce_State()
            return self

        def update(self, owner_object):
            owner_object.animation.closed_anim()

    class Bounce_State(State):
        """打开时的状态"""
        def on_event(self, event):
            if event == 'open':
                return Question.Open_State()
            return self

        def on_enter(self, owner_object):
            owner_object.animation.current_sprite = sprites.Q_BLOCK_OPEN
            if owner_object.contents.__class__.__name__ == 'Coin':
                owner_object.contents.deployed = True
                c.total_score += c.COIN_SCORE
                c.collected_coins += 1
                sounds.coin.play()
            else:
                sounds.powerup_appears.play()
        
        def update(self, owner_object):
            owner_object.animation.bounce_anim()
            owner_object.pos.y = owner_object.animation.new_y
            if owner_object.animation.bounce_iteration > 48:
                owner_object.state_machine.on_event('open')

    class Open_State(State):
        """打开后的状态"""
        def on_event(self, event):
            return self
        
        def on_enter(self, owner_object):
            owner_object.contents.deployed = True

class Brick(Game_Object):
    """砖块类"""
    def __init__(self, rect):
        super(Brick, self).__init__(rect)

        self.animation = self.Animation(self.pos.y)
        self.state_machine = State_Machine(self.Idle_State(), self)

        self.remove = False
    
    def update(self):
        self.state_machine.update()

    def draw(self, pos):
        c.screen.blit(sprites.tile_set, (pos.x, pos.y), sprites.BRICK)

    def instantiate_fragments(self):
        """破碎时实例化片段"""
        level.brick_fragments.append(Brick_Fragment(Vector2(self.pos.x, self.pos.y), Vector2(-0.1, -0.5), Rectangle()))
        level.brick_fragments.append(Brick_Fragment(Vector2(self.pos.x + 24, self.pos.y), Vector2(0.1, -0.5), Rectangle()))
        level.brick_fragments.append(Brick_Fragment(Vector2(self.pos.x + 24, self.pos.y + 24), Vector2(0.1, -0.4), Rectangle()))
        level.brick_fragments.append(Brick_Fragment(Vector2(self.pos.x, self.pos.y + 24), Vector2(-0.1, -0.4), Rectangle()))

    class Animation():
        """包含该类的特定动画变量和函数"""
        def __init__(self, start_height):
            
            self.bounce_iteration = 0
            self.new_y = start_height
            self.start_height = start_height

        def bounce_anim(self):
            self.new_y = self.start_height - self.bounce_anim_function(self.bounce_iteration)
            self.bounce_iteration += 4
            
        def bounce_anim_function(self, bounce_iteration):
            return -abs(bounce_iteration - 24) + 24            

    class Idle_State(State):
        """不与任何事物交互时的状态"""
        def on_event(self, event):
            if event == 'bounce':
                return Brick.Bounce_State()
            elif event == 'break':
                return Brick.Break_State()
            return self

    class Bounce_State(State):
        """小马里奥从下面撞砖时的状态"""
        def on_event(self, event):
            if event == 'idle':
                return Brick.Idle_State()
            return self
        
        def update(self, owner_object):
            owner_object.animation.bounce_anim()
            owner_object.pos.y = owner_object.animation.new_y
            if owner_object.animation.bounce_iteration > 48:
                owner_object.animation.bounce_iteration = 0
                owner_object.state_machine.on_event('idle')

    class Break_State(State):
        """当大马里奥从下面击中砖块时的状态"""
        def __init__(self):
            self.wait_for_frame = 0

        def on_enter(self, owner_object):
            owner_object.instantiate_fragments()
            sounds.brick_smash.play()

        def update(self, owner_object):
            if self.wait_for_frame > 0:
                level.dynamic_colliders.remove(owner_object)
            self.wait_for_frame += 1

class Brick_Fragment(Entity):
    """处理单个砖块及其动画"""
    def __init__(self, pos, vel, rect):
        super(Brick_Fragment, self).__init__(vel, rect)
        self.rect.pos = pos
        self.animation = self.Animation()

    def update(self):
        accelerate(self, 0, c.GRAVITY)
        self.pos += self.vel * c.delta_time
        self.animation.anim()
        self.check_for_destroy()
    
    def check_for_destroy(self):
        """检查实例是否可以被销毁"""
        if self.pos.y > c.SCREEN_SIZE.y:
            level.brick_fragments.remove(self)
    
    def draw(self):
        view_pos = c.camera.to_view_space(self.pos)
        c.screen.blit(sprites.tile_set, (view_pos.x, view_pos.y), self.animation.current_sprite)
    
    class Animation():
        """包含该类的特定动画变量和函数"""
        def __init__(self):
            self.current_sprite = None
            self.anim_frame = 0
            self.anim_timer = c.INITIAL_TIMER_VALUE

        def anim(self):
            self.current_sprite = sprites.BRICK_FRAGMENT[self.anim_frame % 2]
            self.anim_timer += c.delta_time
            if self.anim_timer > 8 * c.delta_time:
                self.anim_frame += 1
                self.anim_timer = 0

class Flagpole(Game_Object):
    """在关卡结束时处理旗杆并触发获胜事件"""
    def __init__(self, rect, flag_pos):
        super(Flagpole, self).__init__(rect)
        self.flag_pos = flag_pos

    def update(self):
        if self.rect.check_collisions([c.mario]) is not None:
            c.mario.mario_states.on_event('win')

        if c.mario.current_mario_state == 'Win_State':
            if not self.flag_pos.y >= self.pos.y + self.rect.h - 60:
                self.flag_pos.y += 4

    def draw_flag(self):
        view_pos = c.camera.to_view_space(self.flag_pos)
        c.screen.blit(sprites.tile_set, (view_pos.x, view_pos.y), sprites.FLAG)
