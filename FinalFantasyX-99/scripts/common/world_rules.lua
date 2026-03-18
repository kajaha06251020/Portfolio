rules.register("on_state_change", function(key, old, new)
  if key == "physical.healed_count" and new > old then
    local depth_dist = world.get_state("depth.distortion")
    world.set_state("depth.distortion", depth_dist + (new - old) * 0.5)
  end
  if key == "depth.crystallization" and new > old then
    local stability = world.get_state("dream.stability")
    world.set_state("dream.stability", math.max(0, stability - (new - old) * 2))
  end
  if key == "dream.stability" and new <= 0 then
    event.trigger("dream_collapse")
    world.set_state("physical.distortion", world.get_state("physical.distortion") + 10)
  end
end)
